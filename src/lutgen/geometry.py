from __future__ import annotations

import functools
import math

import numpy as np
import pyproj

from lutgen.sites import Site


@functools.lru_cache(maxsize=None)
def aeqd_transformer(site: Site) -> pyproj.Transformer:
    """Return a Transformer from WGS84 to AEQD centered on this site.

    AEQD (Azimuthal Equidistant) preserves distance from the projection center,
    which is exactly what we need for radar range computation.
    """
    aeqd = pyproj.CRS(
        proj="aeqd",
        lat_0=site.lat,
        lon_0=site.lon,
        datum="WGS84",
        units="m",
    )
    return pyproj.Transformer.from_crs("EPSG:4326", aeqd, always_xy=True)


def pixel_to_polar(
    site: Site,
    pixel_lat: np.ndarray,
    pixel_lon: np.ndarray,
    xfm: pyproj.Transformer | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map pixel lat/lon arrays to (range_idx, azimuth_idx, mask).

    Returns:
        range_idx: uint16, index into the polar.zarr range axis
        azimuth_idx: uint16, index into the polar.zarr azimuth axis
        mask: uint8, 1 where pixel is within radar coverage, else 0
    """
    if xfm is None:
        xfm = aeqd_transformer(site)
    x_m, y_m = xfm.transform(pixel_lon, pixel_lat)

    range_m = np.sqrt(x_m**2 + y_m**2)

    # 0° = North, 90° = East (clockwise from North, matching radar convention)
    azimuth_deg = (np.degrees(np.arctan2(x_m, y_m)) + 360.0) % 360.0

    range_idx_f = (range_m - site.first_range_gate_m) / site.range_gate_spacing_m
    azimuth_idx_f = azimuth_deg / (360.0 / site.n_azimuths)

    max_range_idx = int(
        math.floor((site.max_range_m - site.first_range_gate_m) / site.range_gate_spacing_m)
    )

    range_idx = np.floor(range_idx_f).astype(np.int32)
    azimuth_idx = np.floor(azimuth_idx_f).astype(np.int32)

    in_range = (range_idx >= 0) & (range_idx < max_range_idx) & (range_m <= site.max_range_m)
    mask = in_range.astype(np.uint8)

    # Zero out indices for masked pixels so downstream code can index safely
    range_idx = np.where(in_range, range_idx, 0).astype(np.uint16)
    azimuth_idx = np.where(in_range, azimuth_idx % site.n_azimuths, 0).astype(np.uint16)

    return range_idx, azimuth_idx, mask


def coverage_bbox_wgs84(site: Site) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) of the site's coverage circle.

    Approximates the great-circle disk bounding box. Some edge tiles returned
    by mercantile.tiles() may have zero in-coverage pixels, which is fine.
    """
    # Degrees of latitude per meter (roughly constant)
    lat_deg_per_m = 1.0 / 111_320.0
    # Degrees of longitude per meter varies with latitude
    lon_deg_per_m = 1.0 / (111_320.0 * math.cos(math.radians(site.lat)))

    delta_lat = site.max_range_m * lat_deg_per_m
    delta_lon = site.max_range_m * lon_deg_per_m

    return (
        site.lon - delta_lon,
        site.lat - delta_lat,
        site.lon + delta_lon,
        site.lat + delta_lat,
    )
