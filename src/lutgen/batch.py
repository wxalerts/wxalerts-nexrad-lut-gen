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
) -> tuple[str, bool, str, int, float, float]:
    """Worker: generate + write one (site, zoom) LUT.

    Returns (label, success, error, n_tiles, compute_s, upload_s).
    n_tiles / compute_s / upload_s are 0 on skip or failure.
    """
    from lutgen.config import Config
    from lutgen.sites import SITE_BY_ICAO

    label = f"{icao}/z{zoom:02d}"
    try:
        config = Config(**config_dict)
        storage = LutStorage(config)
        site = SITE_BY_ICAO[icao]
        if not force and storage.exists("site", site=site, zoom=zoom):
            return label, True, "skip", 0, 0.0, 0.0

        t_compute = time.monotonic()
        lut = generate_site_lut(site, zoom)
        compute_s = time.monotonic() - t_compute

        t_upload = time.monotonic()
        storage.write_site_lut(site, zoom, lut.to_npz_dict())
        upload_s = time.monotonic() - t_upload

        return label, True, "", lut.tile_index.shape[0], compute_s, upload_s
    except Exception:
        return label, False, traceback.format_exc(), 0, 0.0, 0.0


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


def _fmt(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def _render(
    progress: Progress,
    # ordered dict: label → (future, start_time) — insertion order = submission order
    in_flight: dict[str, tuple[concurrent.futures.Future[Any], float]],
    log_lines: deque[str],
    concurrency: int,
) -> Layout:
    now = time.monotonic()

    # Use submission order: the first `concurrency` un-finished tasks are the
    # ones most likely being executed right now.  Avoids the overcounting
    # problem with fut.running() which fires before a worker actually starts.
    items = [(lbl, t0) for lbl, (fut, t0) in in_flight.items() if not fut.done()]
    running_items = items[:concurrency]
    queued_count = max(0, len(items) - concurrency)

    tbl = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tbl.add_column(no_wrap=True)
    tbl.add_column(justify="right", no_wrap=True, style="dim")
    for label, t0 in running_items:
        elapsed = now - t0
        color = "red" if elapsed > 300 else "yellow" if elapsed > 60 else "green"
        tbl.add_row(f"[{color}]{label}[/{color}]", _fmt(elapsed))

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
        title=f"[cyan]Running ({len(running_items)})[/cyan]"
              + (f"  [dim]+{queued_count} queued[/dim]" if queued_count else ""),
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
    log_lines: deque[str] = deque(maxlen=500)
    # Ordered insertion so we can infer running vs queued by position
    in_flight: dict[str, tuple[concurrent.futures.Future[Any], float]] = {}

    progress = _make_progress()
    task_id = progress.add_task("[cyan]Site LUTs", total=len(tasks))

    with (
        Live(_render(progress, in_flight, log_lines, concurrency), refresh_per_second=4, screen=True) as live,
        concurrent.futures.ProcessPoolExecutor(max_workers=concurrency) as pool,
    ):
        for icao, zoom in tasks:
            label = f"{icao}/z{zoom:02d}"
            fut = pool.submit(_run_site_zoom, icao, zoom, config_dict, force)
            in_flight[label] = (fut, time.monotonic())

        for fut in concurrent.futures.as_completed(f for _, (f, _) in in_flight.items()):
            # Find label for this future
            label = next(lbl for lbl, (f, _) in in_flight.items() if f is fut)
            _, t0 = in_flight[label]
            wall_s = time.monotonic() - t0

            _, success, msg, n_tiles, compute_s, upload_s = fut.result()

            if msg == "skip":
                result.skipped.append(label)
                # Don't clutter the log with skips — update description instead
                progress.update(
                    task_id,
                    description=f"[cyan]Site LUTs[/cyan] [dim]({len(result.skipped)} skipped)[/dim]",
                )
            elif success:
                result.succeeded.append(label)
                rate = f"{n_tiles / compute_s:.0f} t/s" if compute_s > 0 else ""
                log_lines.append(
                    f"[green]✓[/green] {label}"
                    f"  [dim]{_fmt(wall_s)}  {n_tiles} tiles"
                    f"  compute {compute_s:.1f}s  upload {upload_s:.1f}s  {rate}[/dim]"
                )
                log.info("done", label=label, wall=_fmt(wall_s), tiles=n_tiles,
                         compute_s=round(compute_s, 1), upload_s=round(upload_s, 1))
            else:
                result.failed.append((label, msg))
                log_lines.append(f"[red bold]✗ {label} FAILED[/red bold]\n[red dim]{msg.strip()}[/red dim]")
                log.error("failed", label=label, error=msg)

            progress.advance(task_id)
            live.update(_render(progress, in_flight, log_lines, concurrency))

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
