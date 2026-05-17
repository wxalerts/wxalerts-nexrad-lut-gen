from __future__ import annotations

import mercantile

from lutgen.tiles import tile_pixel_lonlat, tiles_in_coverage
from tests.conftest import KABR, KMOB


def test_tiles_in_coverage_kmob_z10():
    """KMOB at zoom 10 should have a reasonable number of tiles."""
    tiles = tiles_in_coverage(KMOB, zoom=10)
    # 230 km radius at z10: the bbox pre-filter returns more tiles than the
    # final coverage circle; expect at least 4 and no more than 500
    assert len(tiles) >= 4, f"Expected >= 4 tiles, got {len(tiles)}"
    assert len(tiles) <= 500, f"Expected <= 500 tiles, got {len(tiles)}"


def test_tiles_in_coverage_returns_mercantile_tiles():
    tiles = tiles_in_coverage(KMOB, zoom=10)
    assert all(isinstance(t, mercantile.Tile) for t in tiles)
    assert all(t.z == 10 for t in tiles)


def test_tiles_in_coverage_kabr_z10():
    """Aberdeen, SD is near the northern CONUS boundary — should still work."""
    tiles = tiles_in_coverage(KABR, zoom=10)
    assert len(tiles) >= 4


def test_tile_pixel_lonlat_shape():
    tile = mercantile.Tile(x=250, y=400, z=10)
    lon, lat = tile_pixel_lonlat(tile, tile_size=256)
    assert lon.shape == (256, 256)
    assert lat.shape == (256, 256)


def test_tile_pixel_lonlat_bounds():
    tile = mercantile.Tile(x=250, y=400, z=10)
    bounds = mercantile.bounds(tile)
    lon, lat = tile_pixel_lonlat(tile, tile_size=256)
    # Pixel centers should be within tile bounds (with a small tolerance)
    assert lon.min() >= bounds.west - 1e-6
    assert lon.max() <= bounds.east + 1e-6
    assert lat.min() >= bounds.south - 1e-6
    assert lat.max() <= bounds.north + 1e-6


def test_tile_pixel_lonlat_low_zoom():
    """Low-zoom tiles use the exact Mercator unproject path."""
    tile = mercantile.Tile(x=5, y=5, z=4)
    lon, lat = tile_pixel_lonlat(tile, tile_size=256)
    assert lon.shape == (256, 256)
    assert lat.shape == (256, 256)
