from __future__ import annotations

import functools
import math

import numpy as np
import pyproj

from lutgen.sites import Site

# WGS84 mean Earth radius — spherical haversine error vs geodetic AEQD is
# ≈ 0.2 % at 230 km max range (≈ 250 m, < 1 range gate at 250 m spacing).
_EARTH_RADIUS_M: float = 6_371_008.8


@functools.cache
def aeqd_transformer(site: Site) -> pyproj.Transformer:
    """Return a WGS84→AEQD Transformer centred on this site (used by verify only)."""
    aeqd = pyproj.CRS(
        proj="aeqd",
        lat_0=site.lat,
        lon_0=site.lon,
        datum="WGS84",
        units="m",
    )
    return pyproj.Transformer.from_crs("EPSG:4326", aeqd, always_xy=True)


def haversine_dist(
    lat0: float,
    lon0: float,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray:
    """Vectorised great-circle distance (metres) from scalar (lat0, lon0) to arrays."""
    lat0_r = math.radians(lat0)
    lon0_r = math.radians(lon0)
    lat_r = np.radians(lats)
    lon_r = np.radians(lons)
    dlat = lat_r - lat0_r
    dlon = lon_r - lon0_r
    a = np.sin(dlat * 0.5) ** 2 + math.cos(lat0_r) * np.cos(lat_r) * np.sin(dlon * 0.5) ** 2
    return 2.0 * _EARTH_RADIUS_M * np.arcsin(np.sqrt(a.clip(0.0, 1.0)))


def pixel_to_polar(
    site: Site,
    pixel_lat: np.ndarray,
    pixel_lon: np.ndarray,
    xfm: pyproj.Transformer | None = None,  # no longer used; kept for API compatibility
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map pixel lat/lon arrays to (range_idx, azimuth_idx, mask).

    Uses spherical Haversine + forward-bearing formulas (no PROJ call).
    Accepts arrays of any shape, including batched (N, H, W).

    Returns:
        range_idx:   uint16, index into the polar.zarr range axis
        azimuth_idx: uint16, index into the polar.zarr azimuth axis
        mask:        uint8, 1 where pixel is within radar coverage, else 0
    """
    lat0 = math.radians(site.lat)
    lon0 = math.radians(site.lon)
    cos_lat0 = math.cos(lat0)
    sin_lat0 = math.sin(lat0)

    lat_r = np.radians(pixel_lat)
    lon_r = np.radians(pixel_lon)

    # Cast scalar constants to the array dtype so float32 inputs stay float32
    # throughout and don't get silently upcast to float64.
    dt = lat_r.dtype
    _lat0     = dt.type(lat0)
    _lon0     = dt.type(lon0)
    _cos_lat0 = dt.type(cos_lat0)
    _sin_lat0 = dt.type(sin_lat0)
    _2R       = dt.type(2.0 * _EARTH_RADIUS_M)

    dlat = lat_r - _lat0
    dlon = lon_r - _lon0

    # Great-circle distance via Haversine
    a = np.sin(dlat * 0.5) ** 2 + _cos_lat0 * np.cos(lat_r) * np.sin(dlon * 0.5) ** 2
    range_m = _2R * np.arcsin(np.sqrt(a.clip(dt.type(0.0), dt.type(1.0))))

    # Forward bearing: 0° = North, clockwise — matches NEXRAD convention
    x = np.cos(lat_r) * np.sin(dlon)
    y = _cos_lat0 * np.sin(lat_r) - _sin_lat0 * np.cos(lat_r) * np.cos(dlon)
    azimuth_deg = (np.degrees(np.arctan2(x, y)) + dt.type(360.0)) % dt.type(360.0)

    range_idx_f = (range_m - dt.type(site.first_range_gate_m)) / dt.type(site.range_gate_spacing_m)
    azimuth_idx_f = azimuth_deg / dt.type(360.0 / site.n_azimuths)
    max_range_idx = int(
        math.floor((site.max_range_m - site.first_range_gate_m) / site.range_gate_spacing_m)
    )

    range_idx = np.floor(range_idx_f).astype(np.int32)
    azimuth_idx = np.floor(azimuth_idx_f).astype(np.int32)

    in_range = (range_idx >= 0) & (range_idx < max_range_idx) & (range_m <= dt.type(site.max_range_m))
    mask = in_range.astype(np.uint8)
    range_idx = np.where(in_range, range_idx, 0).astype(np.uint16)
    azimuth_idx = np.where(in_range, azimuth_idx % site.n_azimuths, 0).astype(np.uint16)

    return range_idx, azimuth_idx, mask


def coverage_bbox_wgs84(site: Site) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) of the site's coverage circle."""
    lat_deg_per_m = 1.0 / 111_320.0
    lon_deg_per_m = 1.0 / (111_320.0 * math.cos(math.radians(site.lat)))

    delta_lat = site.max_range_m * lat_deg_per_m
    delta_lon = site.max_range_m * lon_deg_per_m

    return (
        site.lon - delta_lon,
        site.lat - delta_lat,
        site.lon + delta_lon,
        site.lat + delta_lat,
    )
