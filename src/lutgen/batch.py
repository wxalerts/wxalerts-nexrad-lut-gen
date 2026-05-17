from __future__ import annotations

import concurrent.futures
import traceback
from dataclasses import dataclass, field
from typing import Any

import structlog
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from lutgen.config import Config
from lutgen.mosaic_lut import generate_mosaic_lut, split_mosaic_lut
from lutgen.site_lut import generate_site_lut
from lutgen.sites import Site
from lutgen.storage import LutStorage

log = structlog.get_logger()


@dataclass
class BatchResult:
    succeeded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


# ── per-task callables (must be top-level for pickling) ──────────────────────

def _run_site_zoom(
    icao: str,
    zoom: int,
    config_dict: dict[str, Any],  # serialisable form of Config
    force: bool,
) -> tuple[str, bool, str]:
    """Worker: generate one (site, zoom) LUT. Returns (label, success, error)."""
    from lutgen.config import Config
    from lutgen.sites import SITE_BY_ICAO

    label = f"{icao}/z{zoom:02d}"
    try:
        config = Config(**config_dict)
        storage = LutStorage(config)
        site = SITE_BY_ICAO[icao]
        if not force and storage.exists("site", site=site, zoom=zoom):
            return label, True, "skip"
        result = generate_site_lut(site, zoom)
        storage.write_site_lut(site, zoom, result.to_npz_dict())
        return label, True, ""
    except Exception:
        return label, False, traceback.format_exc()


def _run_mosaic_zoom(
    zoom: int,
    config_dict: dict[str, Any],
    force: bool,
) -> tuple[str, bool, str]:
    label = f"mosaic/z{zoom:02d}"
    try:
        config = Config(**config_dict)
        storage = LutStorage(config)
        if not force and storage.exists("mosaic", zoom=zoom, part=0):
            return label, True, "skip"
        result = generate_mosaic_lut(zoom)
        parts = split_mosaic_lut(result)
        for part_idx, part in enumerate(parts):
            storage.write_mosaic_lut(zoom, part_idx, part.to_npz_dict())
        return label, True, ""
    except Exception:
        return label, False, traceback.format_exc()


# ── public API ────────────────────────────────────────────────────────────────

def generate_all_sites(
    sites: list[Site],
    zooms: list[int],
    concurrency: int,
    config: Config,
    force: bool = False,
) -> BatchResult:
    config_dict: dict[str, Any] = config.model_dump()
    # Convert Path to str for pickling
    config_dict["output_local_dir"] = str(config_dict["output_local_dir"])

    tasks = [(site.icao, zoom) for site in sites for zoom in zooms]
    result = BatchResult()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task_id = progress.add_task("Generating site LUTs", total=len(tasks))

        with concurrent.futures.ProcessPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_run_site_zoom, icao, zoom, config_dict, force): (icao, zoom)
                for icao, zoom in tasks
            }
            for fut in concurrent.futures.as_completed(futures):
                label, success, msg = fut.result()
                if msg == "skip":
                    result.skipped.append(label)
                    log.debug("skipped", label=label)
                elif success:
                    result.succeeded.append(label)
                    log.info("done", label=label)
                else:
                    result.failed.append((label, msg))
                    log.error("failed", label=label, error=msg)
                progress.advance(task_id)

    return result


def generate_full_mosaic(
    zooms: list[int],
    config: Config,
    force: bool = False,
) -> BatchResult:
    config_dict: dict[str, Any] = config.model_dump()
    config_dict["output_local_dir"] = str(config_dict["output_local_dir"])

    result = BatchResult()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task_id = progress.add_task("Generating mosaic LUTs", total=len(zooms))

        # Mosaic zooms run sequentially within zoom (each is a big job) but
        # individual zooms could run in parallel if memory allows.
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(zooms), 4)) as pool:
            futures = {pool.submit(_run_mosaic_zoom, zoom, config_dict, force): zoom for zoom in zooms}
            for fut in concurrent.futures.as_completed(futures):
                label, success, msg = fut.result()
                if msg == "skip":
                    result.skipped.append(label)
                elif success:
                    result.succeeded.append(label)
                    log.info("done", label=label)
                else:
                    result.failed.append((label, msg))
                    log.error("failed", label=label, error=msg)
                progress.advance(task_id)

    return result
