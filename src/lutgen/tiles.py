from __future__ import annotations

import mercantile
import numpy as np
import pyproj

from lutgen.geometry import coverage_bbox_wgs84
from lutgen.sites import Site

# Web Mercator (EPSG:3857) -> WGS84, vectorized via pyproj
_WEBMERC_TO_WGS84 = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def tiles_in_coverage(site: Site, zoom: int) -> list[mercantile.Tile]:
    """Return all Web Mercator tiles at zoom that intersect the site's coverage area."""
    bbox = coverage_bbox_wgs84(site)
    return list(mercantile.tiles(bbox[0], bbox[1], bbox[2], bbox[3], zooms=zoom))


def tile_pixel_lonlat(
    tile: mercantile.Tile, tile_size: int = 256
) -> tuple[np.ndarray, np.ndarray]:
    """Return (lon, lat) arrays of shape (tile_size, tile_size) for pixel centers.

    Low-zoom tiles (z <= 7) use pyproj to invert Web Mercator exactly.
    High-zoom tiles use linear interpolation in WGS84 (accurate enough).
    """
    if tile.z <= 7:
        xy_bounds = mercantile.xy_bounds(tile)
        x_step = (xy_bounds.right - xy_bounds.left) / tile_size
        y_step = (xy_bounds.top - xy_bounds.bottom) / tile_size

        xs = xy_bounds.left + (np.arange(tile_size) + 0.5) * x_step
        ys = xy_bounds.top - (np.arange(tile_size) + 0.5) * y_step

        xv, yv = np.meshgrid(xs, ys)
        lon_flat, lat_flat = _WEBMERC_TO_WGS84.transform(xv.ravel(), yv.ravel())
        lon = lon_flat.reshape(tile_size, tile_size)
        lat = lat_flat.reshape(tile_size, tile_size)
    else:
        bounds = mercantile.bounds(tile)
        lon_step = (bounds.east - bounds.west) / tile_size
        lat_step = (bounds.north - bounds.south) / tile_size

        lons = bounds.west + (np.arange(tile_size) + 0.5) * lon_step
        lats = bounds.north - (np.arange(tile_size) + 0.5) * lat_step

        lon, lat = np.meshgrid(lons, lats)

    return lon.astype(np.float64), lat.astype(np.float64)
