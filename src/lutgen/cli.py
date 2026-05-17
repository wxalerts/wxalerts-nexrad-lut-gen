from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import typer
from rich.console import Console
from rich.table import Table

from lutgen.config import Config
from lutgen.sites import SITE_BY_ICAO, SITES

app = typer.Typer(name="lutgen", help="NEXRAD LUT generator", no_args_is_help=True)
sites_app = typer.Typer(help="Per-site LUT commands", no_args_is_help=True)
mosaic_app = typer.Typer(help="Mosaic LUT commands", no_args_is_help=True)
app.add_typer(sites_app, name="sites")
app.add_typer(mosaic_app, name="mosaic")

console = Console()
err_console = Console(stderr=True)

_DEFAULT_SITE_ZOOMS = "10,11,12,13,14"
_DEFAULT_MOSAIC_ZOOMS = "4,5,6,7,8,9"


def _parse_zooms(zooms_str: str) -> list[int]:
    try:
        return [int(z.strip()) for z in zooms_str.split(",")]
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid zoom list: {zooms_str!r}") from exc


def _make_config(
    output_local: Path | None,
    output_minio: str | None,
) -> Config:
    overrides: dict[str, Any] = {}
    if output_local:
        overrides["output_local_dir"] = output_local
    if output_minio:
        overrides["output_minio_url"] = output_minio
    return Config(**overrides)


def _setup_logging(level: str = "INFO") -> None:
    import logging

    import structlog

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


# ── lutgen sites generate ─────────────────────────────────────────────────────

@sites_app.command("generate")
def sites_generate(
    site: str | None = typer.Option(None, "--site", help="ICAO code of a single site"),
    all_sites: bool = typer.Option(False, "--all", help="Generate for all sites in registry"),
    zooms: str = typer.Option(_DEFAULT_SITE_ZOOMS, "--zoom", help="Comma-separated zoom levels"),
    output_local: Path | None = typer.Option(None, "--output-local"),  # noqa: B008
    output_minio: str | None = typer.Option(None, "--output-minio"),  # noqa: B008
    concurrency: int = typer.Option(8, "--concurrency"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing LUTs"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing"),
) -> None:
    """Generate per-site LUTs."""
    _setup_logging()

    if not site and not all_sites:
        err_console.print("[red]Specify --site ICAO or --all[/red]")
        raise typer.Exit(1)

    zoom_list = _parse_zooms(zooms)
    config = _make_config(output_local, output_minio)

    if site:
        if site not in SITE_BY_ICAO:
            err_console.print(f"[red]Unknown site: {site}[/red]")
            raise typer.Exit(1)
        selected = [SITE_BY_ICAO[site]]
    else:
        selected = SITES

    from lutgen.batch import generate_all_sites

    result = generate_all_sites(
        sites=selected,
        zooms=zoom_list,
        concurrency=concurrency,
        config=config,
        force=force or not skip_existing,
    )

    console.print(
        f"[green]Done.[/green] {len(result.succeeded)} succeeded, "
        f"{len(result.skipped)} skipped, {len(result.failed)} failed."
    )
    if result.failed:
        for label, err in result.failed:
            err_console.print(f"[red]FAILED[/red] {label}:\n{err}")
        raise typer.Exit(1)


# ── lutgen mosaic generate ────────────────────────────────────────────────────

@mosaic_app.command("generate")
def mosaic_generate(
    zooms: str = typer.Option(_DEFAULT_MOSAIC_ZOOMS, "--zoom"),
    output_local: Path | None = typer.Option(None, "--output-local"),  # noqa: B008
    output_minio: str | None = typer.Option(None, "--output-minio"),  # noqa: B008
    force: bool = typer.Option(False, "--force"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing"),
) -> None:
    """Generate mosaic LUTs."""
    _setup_logging()
    zoom_list = _parse_zooms(zooms)
    config = _make_config(output_local, output_minio)

    from lutgen.batch import generate_full_mosaic

    result = generate_full_mosaic(zoom_list, config, force=force or not skip_existing)

    console.print(
        f"[green]Done.[/green] {len(result.succeeded)} succeeded, "
        f"{len(result.skipped)} skipped, {len(result.failed)} failed."
    )
    if result.failed:
        for label, err in result.failed:
            err_console.print(f"[red]FAILED[/red] {label}:\n{err}")
        raise typer.Exit(1)


# ── lutgen list-sites ─────────────────────────────────────────────────────────

@app.command("list-sites")
def list_sites() -> None:
    """Print the embedded site registry."""
    table = Table(title=f"NEXRAD Sites ({len(SITES)} total)")
    table.add_column("ICAO", style="bold cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Lat", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Elev (m)", justify="right")
    table.add_column("Azimuths", justify="right")

    for s in sorted(SITES, key=lambda x: x.icao):
        table.add_row(
            s.icao,
            s.name,
            s.site_type,
            f"{s.lat:.4f}",
            f"{s.lon:.4f}",
            f"{s.elevation_m:.1f}",
            str(s.n_azimuths),
        )
    console.print(table)


# ── lutgen verify ─────────────────────────────────────────────────────────────

@app.command("verify")
def verify(
    lut_file: Path = typer.Argument(..., help="Path to a .npz LUT file"),  # noqa: B008
    site: str | None = typer.Option(None, "--site", help="ICAO site code (required for --check-geometry)"),
    zoom: int | None = typer.Option(None, "--zoom", help="Zoom level (required for --check-geometry)"),
    check_geometry: bool = typer.Option(False, "--check-geometry", help="Run polar geometry consistency check"),
) -> None:
    """Validate the structure of a generated .npz LUT file.

    Add --check-geometry --site ICAO --zoom N to also verify that the stored
    polar indices are geometrically consistent with each tile's location.

    Example:
        lutgen verify sites/KMOB/z12.npz --check-geometry --site KMOB --zoom 12
    """
    if not lut_file.exists():
        err_console.print(f"[red]File not found: {lut_file}[/red]")
        raise typer.Exit(1)

    data = np.load(str(lut_file))
    keys = set(data.files)
    console.print(f"Keys: {sorted(keys)}")

    errors: list[str] = []

    if "tile_index" in keys:
        ti = data["tile_index"]
        console.print(f"  tile_index: {ti.shape} {ti.dtype}")
        if ti.ndim != 2 or ti.shape[1] != 2:
            errors.append("tile_index must be (n_tiles, 2)")

    for key in ("range_idx", "azimuth_idx"):
        if key in keys:
            arr = data[key]
            console.print(f"  {key}: {arr.shape} {arr.dtype}")
            if arr.dtype != np.uint16:
                errors.append(f"{key} must be uint16, got {arr.dtype}")

    if "mask" in keys:
        arr = data["mask"]
        console.print(f"  mask: {arr.shape} {arr.dtype}")
        if arr.dtype != np.uint8:
            errors.append(f"mask must be uint8, got {arr.dtype}")

    if "contribution_offsets" in keys:
        co = data["contribution_offsets"]
        console.print(f"  contribution_offsets: {co.shape} {co.dtype}")
        if not all(co[i] <= co[i + 1] for i in range(len(co) - 1)):
            errors.append("contribution_offsets must be non-decreasing")

    if errors:
        for e in errors:
            err_console.print(f"[red]ERROR[/red]: {e}")
        raise typer.Exit(1)

    console.print("[green]Structure OK[/green]")

    # ── optional geometry check ───────────────────────────────────────────────
    if check_geometry:
        if not site or zoom is None:
            err_console.print("[red]--check-geometry requires --site ICAO and --zoom N[/red]")
            raise typer.Exit(1)
        if site not in SITE_BY_ICAO:
            err_console.print(f"[red]Unknown site: {site}[/red]")
            raise typer.Exit(1)

        import math
        import mercantile
        from lutgen.geometry import aeqd_transformer

        site_obj    = SITE_BY_ICAO[site]
        transformer = aeqd_transformer(site_obj)
        tile_index  = data["tile_index"]
        range_idx   = data["range_idx"]
        azimuth_idx = data["azimuth_idx"]
        mask        = data["mask"]

        range_tol   = 5
        azimuth_tol = 2
        geo_errors: list[str] = []
        n_checked   = 0

        for row in range(tile_index.shape[0]):
            tx, ty = int(tile_index[row, 0]), int(tile_index[row, 1])
            m = mask[row]
            h, w = m.shape
            cy, cx = h // 2, w // 2
            if m[cy, cx] == 0:
                continue  # center pixel outside coverage — skip

            bounds     = mercantile.bounds(mercantile.Tile(x=tx, y=ty, z=zoom))
            center_lon = (bounds.west + bounds.east) / 2
            center_lat = (bounds.south + bounds.north) / 2

            x_aeqd, y_aeqd = transformer.transform(center_lon, center_lat)
            range_m         = math.hypot(x_aeqd, y_aeqd)
            exp_range_idx   = int(
                (range_m - site_obj.first_range_gate_m) / site_obj.range_gate_spacing_m
            )
            exp_az_deg = (math.degrees(math.atan2(x_aeqd, y_aeqd)) + 360) % 360
            exp_az_idx = int(exp_az_deg / (360.0 / site_obj.n_azimuths))

            act_range = int(range_idx[row][cy, cx])
            act_az    = int(azimuth_idx[row][cy, cx])

            range_diff = abs(act_range - exp_range_idx)
            raw_diff   = abs(act_az - exp_az_idx)
            az_diff    = min(raw_diff, site_obj.n_azimuths - raw_diff)

            n_checked += 1
            if range_diff > range_tol:
                geo_errors.append(
                    f"Tile ({tx},{ty}): range expected={exp_range_idx} actual={act_range} Δ{range_diff}"
                )
            if az_diff > azimuth_tol:
                geo_errors.append(
                    f"Tile ({tx},{ty}): azimuth expected={exp_az_idx} actual={act_az} Δ{az_diff}"
                )
            if len(geo_errors) >= 20:
                break

        console.print(f"Geometry check: {n_checked} center-covered tiles checked")
        if geo_errors:
            for e in geo_errors:
                err_console.print(f"[red]GEOMETRY ERROR[/red]: {e}")
            raise typer.Exit(1)
        console.print("[green]Geometry OK[/green]")
