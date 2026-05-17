from __future__ import annotations

import concurrent.futures
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import structlog
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

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
    config_dict: dict[str, Any],
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


# ── TUI helpers ───────────────────────────────────────────────────────────────

def _make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        expand=True,
    )


def _render(
    progress: Progress,
    submitted: dict[concurrent.futures.Future[Any], tuple[str, float]],
    log_lines: deque[str],
) -> Layout:
    now = time.monotonic()

    # Running table — only futures the pool is actually executing
    running: list[tuple[str, float]] = [
        (label, now - t0)
        for fut, (label, t0) in submitted.items()
        if fut.running()
    ]
    running.sort(key=lambda x: x[1], reverse=True)  # longest-running first

    tbl = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tbl.add_column(no_wrap=True)
    tbl.add_column(justify="right", no_wrap=True, style="dim")
    for label, elapsed in running:
        color = "red" if elapsed > 300 else "yellow" if elapsed > 60 else "green"
        mins, secs = divmod(int(elapsed), 60)
        tbl.add_row(
            f"[{color}]{label}[/{color}]",
            f"{mins}:{secs:02d}",
        )

    pending = sum(1 for fut in submitted if not fut.done() and not fut.running())

    layout = Layout()
    layout.split_column(
        Layout(name="progress", size=4),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="running", ratio=1),
        Layout(name="log", ratio=2),
    )
    layout["progress"].update(Panel(progress, padding=(0, 1)))
    layout["running"].update(Panel(
        tbl,
        title=f"[cyan]Running ({len(running)})[/cyan]"
              + (f"  [dim]+{pending} queued[/dim]" if pending else ""),
        border_style="cyan",
    ))
    layout["log"].update(Panel(
        Text.from_markup("\n".join(log_lines)),
        title="[bold]Log[/bold]",
        border_style="dim",
    ))
    return layout


# ── public API ────────────────────────────────────────────────────────────────

def generate_all_sites(
    sites: list[Site],
    zooms: list[int],
    concurrency: int,
    config: Config,
    force: bool = False,
) -> BatchResult:
    config_dict: dict[str, Any] = config.model_dump()
    config_dict["output_local_dir"] = str(config_dict["output_local_dir"])

    tasks = [(site.icao, zoom) for site in sites for zoom in zooms]
    result = BatchResult()
    log_lines: deque[str] = deque(maxlen=200)
    submitted: dict[concurrent.futures.Future[Any], tuple[str, float]] = {}

    progress = _make_progress()
    task_id = progress.add_task("[cyan]Site LUTs", total=len(tasks))

    with (
        Live(_render(progress, submitted, log_lines), refresh_per_second=4, screen=True) as live,
        concurrent.futures.ProcessPoolExecutor(max_workers=concurrency) as pool,
    ):
            for icao, zoom in tasks:
                label = f"{icao}/z{zoom:02d}"
                fut = pool.submit(_run_site_zoom, icao, zoom, config_dict, force)
                submitted[fut] = (label, time.monotonic())

            for fut in concurrent.futures.as_completed(submitted):
                label, t0 = submitted[fut]
                elapsed = time.monotonic() - t0
                mins, secs = divmod(int(elapsed), 60)
                dur = f"{mins}:{secs:02d}"

                _, success, msg = fut.result()
                if msg == "skip":
                    result.skipped.append(label)
                    log_lines.append(f"[dim]~ {label}[/dim]")
                    log.debug("skipped", label=label)
                elif success:
                    result.succeeded.append(label)
                    log_lines.append(f"[green]✓[/green] {label}  [dim]{dur}[/dim]")
                    log.info("done", label=label, elapsed=dur)
                else:
                    result.failed.append((label, msg))
                    log_lines.append(f"[red]✗ {label} FAILED[/red]")
                    log.error("failed", label=label, error=msg)

                progress.advance(task_id)
                live.update(_render(progress, submitted, log_lines))

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
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task_id = progress.add_task("Mosaic LUTs", total=len(zooms))

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
