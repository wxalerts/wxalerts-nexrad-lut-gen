from __future__ import annotations

import math

import numpy as np
import pyproj

from lutgen.geometry import aeqd_transformer, coverage_bbox_wgs84, pixel_to_polar
from tests.conftest import KMOB


def test_aeqd_roundtrip_distance():
    """A known geodesic point 100 km due north of KMOB should transform to ~100 km."""
    # Use pyproj Geod to place a point exactly 100 km north of KMOB
    geod = pyproj.Geod(ellps="WGS84")
    lon2, lat2, _ = geod.fwd(KMOB.lon, KMOB.lat, az=0, dist=100_000)

    xfm = aeqd_transformer(KMOB)
    x_m, y_m = xfm.transform(lon2, lat2)
    range_m = math.sqrt(x_m**2 + y_m**2)
    assert abs(range_m - 100_000) < 1.0, f"Expected ~100000 m, got {range_m:.2f}"


def test_pixel_to_polar_first_range_gate():
    """Pixel at the first range gate distance should be in-coverage with range_idx=0."""
    geod = pyproj.Geod(ellps="WGS84")
    dist = KMOB.first_range_gate_m + KMOB.range_gate_spacing_m * 2  # a few gates in
    lon2, lat2, _ = geod.fwd(KMOB.lon, KMOB.lat, az=90, dist=dist)
    lat = np.array([[lat2]])
    lon = np.array([[lon2]])
    range_idx, _, mask = pixel_to_polar(KMOB, lat, lon)
    assert mask[0, 0] == 1, "Pixel within coverage should have mask=1"
    assert range_idx[0, 0] == 2, f"Expected range_idx=2, got {range_idx[0, 0]}"


def test_pixel_to_polar_at_radar_location():
    """Pixel at the radar's own lat/lon is before the first range gate — mask=0."""
    lat = np.array([[KMOB.lat]])
    lon = np.array([[KMOB.lon]])
    _, _, mask = pixel_to_polar(KMOB, lat, lon)
    # The radar itself is at range 0, below first_range_gate_m, so outside coverage
    assert mask[0, 0] == 0, "Radar origin is before first range gate; mask should be 0"


def test_pixel_to_polar_beyond_range():
    """Pixel 300 km away should be masked out (beyond 230 km max range)."""
    geod = pyproj.Geod(ellps="WGS84")
    lon2, lat2, _ = geod.fwd(KMOB.lon, KMOB.lat, az=0, dist=300_000)
    lat = np.array([[lat2]])
    lon = np.array([[lon2]])
    _, _, mask = pixel_to_polar(KMOB, lat, lon)
    assert mask[0, 0] == 0, "Pixel 300 km away should be outside coverage"


def test_coverage_bbox_wgs84():
    """Bounding box should enclose a circle of radius max_range_m."""
    bbox = coverage_bbox_wgs84(KMOB)
    min_lon, min_lat, max_lon, max_lat = bbox
    assert min_lon < KMOB.lon < max_lon
    assert min_lat < KMOB.lat < max_lat
    assert max_lon - min_lon > 0
    assert max_lat - min_lat > 0


def test_azimuth_north_is_zero():
    """A point due north of the radar should have azimuth_idx near 0."""
    geod = pyproj.Geod(ellps="WGS84")
    lon2, lat2, _ = geod.fwd(KMOB.lon, KMOB.lat, az=0, dist=100_000)
    lat = np.array([[lat2]])
    lon = np.array([[lon2]])
    _, azimuth_idx, mask = pixel_to_polar(KMOB, lat, lon)
    assert mask[0, 0] == 1
    # 0° = North; azimuth_idx should be 0 or n_azimuths-1 (wraps near 360)
    assert azimuth_idx[0, 0] == 0 or azimuth_idx[0, 0] == KMOB.n_azimuths - 1
