"""LUT self-consistency tests.

Validates that the polar indices stored in a LUT are geometrically consistent
with the tile's geographic position. No polar.zarr data needed — this checks
the LUT against the geometry that should have produced it.
"""

from __future__ import annotations

import math
from pathlib import Path

import mercantile
import numpy as np
import pytest

from lutgen.geometry import aeqd_transformer
from lutgen.sites import SITE_BY_ICAO, Site


# ── geometry validation helpers ───────────────────────────────────────────────

def _validate_lut_tile(
    site: Site,
    zoom: int,
    tile_x: int,
    tile_y: int,
    range_idx_tile: np.ndarray,    # (H, W) uint16
    azimuth_idx_tile: np.ndarray,  # (H, W) uint16
    mask_tile: np.ndarray,         # (H, W) uint8
    transformer,
    range_tol: int = 5,
    azimuth_tol: int = 2,
) -> list[dict]:
    """Validate one tile's LUT entries against expected polar coords.

    Checks the tile center pixel (H//2, W//2). Returns a list of error dicts
    (empty if everything checks out or the center pixel has no coverage).
    """
    h, w = mask_tile.shape
    cy, cx = h // 2, w // 2

    if mask_tile[cy, cx] == 0:
        return []  # center pixel outside coverage — nothing to validate

    tile = mercantile.Tile(x=tile_x, y=tile_y, z=zoom)
    bounds = mercantile.bounds(tile)
    center_lon = (bounds.west + bounds.east) / 2
    center_lat = (bounds.south + bounds.north) / 2

    # Project to AEQD (x=East m, y=North m) — matches pixel_to_polar convention
    x_aeqd, y_aeqd = transformer.transform(center_lon, center_lat)

    expected_range_m = math.hypot(x_aeqd, y_aeqd)
    expected_range_idx = int(
        (expected_range_m - site.first_range_gate_m) / site.range_gate_spacing_m
    )

    # 0° = North, clockwise — matches pixel_to_polar's arctan2(x, y) convention
    expected_azimuth_deg = (math.degrees(math.atan2(x_aeqd, y_aeqd)) + 360) % 360
    expected_azimuth_idx = int(expected_azimuth_deg / (360.0 / site.n_azimuths))

    actual_range   = int(range_idx_tile[cy, cx])
    actual_azimuth = int(azimuth_idx_tile[cy, cx])

    range_diff = abs(actual_range - expected_range_idx)
    raw_az_diff = abs(actual_azimuth - expected_azimuth_idx)
    azimuth_diff = min(raw_az_diff, site.n_azimuths - raw_az_diff)  # wraparound

    errors = []
    if range_diff > range_tol:
        errors.append({
            "kind": "range",
            "tile_xy": (tile_x, tile_y),
            "tile_center_lonlat": (center_lon, center_lat),
            "expected": expected_range_idx,
            "actual": actual_range,
            "diff": range_diff,
        })
    if azimuth_diff > azimuth_tol:
        errors.append({
            "kind": "azimuth",
            "tile_xy": (tile_x, tile_y),
            "tile_center_lonlat": (center_lon, center_lat),
            "expected": expected_azimuth_idx,
            "actual": actual_azimuth,
            "diff": azimuth_diff,
        })
    return errors


def _validate_full_lut(
    lut_path: Path,
    site_code: str,
    zoom: int,
    range_tol: int = 5,
    azimuth_tol: int = 2,
    max_errors_to_report: int = 20,
) -> tuple[int, int, list[dict]]:
    """Validate every tile in a LUT file.

    Returns (n_checked, n_passed, errors). Bails out early after
    max_errors_to_report errors to keep failure output readable.
    """
    site = SITE_BY_ICAO[site_code]
    lut  = np.load(str(lut_path))

    tile_index  = lut["tile_index"]
    range_idx   = lut["range_idx"]
    azimuth_idx = lut["azimuth_idx"]
    mask        = lut["mask"]

    xfm = aeqd_transformer(site)

    all_errors: list[dict] = []
    n_checked = 0

    for row in range(tile_index.shape[0]):
        tx, ty = int(tile_index[row, 0]), int(tile_index[row, 1])
        errors = _validate_lut_tile(
            site, zoom, tx, ty,
            range_idx[row], azimuth_idx[row], mask[row],
            xfm, range_tol, azimuth_tol,
        )
        if errors:
            all_errors.extend(errors)
        n_checked += 1
        if len(all_errors) >= max_errors_to_report:
            break

    bad_tiles = len({e["tile_xy"] for e in all_errors})
    n_passed  = n_checked - bad_tiles
    return n_checked, n_passed, all_errors


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def generated_lut_dir(tmp_path_factory):
    """Generate LUTs for representative sites once per test module.

    Uses z10 for most sites (fast, ~100-200 tiles) and z12 for two sites to
    exercise a finer zoom. z14 is skipped — it has ~40k tiles and is too slow
    for unit tests.
    """
    from lutgen.site_lut import generate_site_lut

    out_dir = tmp_path_factory.mktemp("luts")

    site_zooms = [
        ("KMOB", 10),
        ("KMOB", 12),
        ("KABR", 10),
        ("KARX", 12),
        ("KFTG", 10),
        ("KAMX", 10),
    ]

    for site_code, zoom in site_zooms:
        site   = SITE_BY_ICAO[site_code]
        result = generate_site_lut(site, zoom=zoom)
        dest   = out_dir / "sites" / site_code / f"z{zoom}.npz"
        dest.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(dest), **result.to_npz_dict())

    return out_dir


# ── tests ─────────────────────────────────────────────────────────────────────

def test_kmob_z10_lut_self_consistent(generated_lut_dir):
    """KMOB z10 LUT has geometrically consistent polar coordinates."""
    lut_path = generated_lut_dir / "sites" / "KMOB" / "z10.npz"
    assert lut_path.exists(), f"LUT not generated at {lut_path}"

    n_checked, n_passed, errors = _validate_full_lut(lut_path, "KMOB", 10)

    if errors:
        lines = [f"LUT validation failed: {len(errors)} errors across {n_checked} tiles"]
        for e in errors[:10]:
            lines.append(
                f"  Tile {e['tile_xy']} @ {e['tile_center_lonlat']}: "
                f"{e['kind']} expected={e['expected']} actual={e['actual']} (Δ{e['diff']})"
            )
        pytest.fail("\n".join(lines))

    assert n_passed == n_checked, f"{n_checked - n_passed} tiles failed geometry check"


@pytest.mark.parametrize("site_code,zoom", [
    ("KMOB", 10),   # Gulf Coast, normal coverage
    ("KMOB", 12),
    ("KABR", 10),   # Northern plains
    ("KARX", 12),   # Upper Midwest
    ("KFTG", 10),   # Mountain West (Denver)
    ("KAMX", 10),   # South Florida, near CONUS edge
])
def test_lut_self_consistency_multi_site(site_code, zoom, generated_lut_dir):
    """LUTs for representative sites have correct polar index geometry."""
    lut_path = generated_lut_dir / "sites" / site_code / f"z{zoom}.npz"
    if not lut_path.exists():
        pytest.skip(f"LUT not available at {lut_path}")

    n_checked, n_passed, errors = _validate_full_lut(lut_path, site_code, zoom)
    assert not errors, (
        f"LUT geometry check failed for {site_code} z{zoom}: "
        + "; ".join(
            f"tile {e['tile_xy']} {e['kind']} Δ{e['diff']}"
            for e in errors[:5]
        )
    )
