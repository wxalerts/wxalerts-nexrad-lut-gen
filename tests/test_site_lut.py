from __future__ import annotations

import numpy as np

from lutgen.site_lut import SiteLutResult
from lutgen.tiles import tiles_in_coverage
from tests.conftest import KMOB


def test_generate_site_lut_kmob_z14_nonempty(kmob_z14_lut: SiteLutResult) -> None:
    assert kmob_z14_lut.tile_index.shape[0] > 0, "Expected at least one tile in KMOB z14 LUT"


def test_generate_site_lut_dtypes(kmob_z14_lut: SiteLutResult) -> None:
    assert kmob_z14_lut.tile_index.dtype == np.int32
    assert kmob_z14_lut.range_idx.dtype == np.uint16
    assert kmob_z14_lut.azimuth_idx.dtype == np.uint16
    assert kmob_z14_lut.mask.dtype == np.uint8


def test_generate_site_lut_shapes_consistent(kmob_z14_lut: SiteLutResult) -> None:
    n = kmob_z14_lut.tile_index.shape[0]
    ts = kmob_z14_lut.range_idx.shape[1]  # tile_size used by the fixture
    assert kmob_z14_lut.range_idx.shape[0] == n
    assert kmob_z14_lut.azimuth_idx.shape[0] == n
    assert kmob_z14_lut.mask.shape[0] == n
    assert kmob_z14_lut.range_idx.shape[1:] == (ts, ts)
    assert kmob_z14_lut.azimuth_idx.shape[1:] == (ts, ts)
    assert kmob_z14_lut.mask.shape[1:] == (ts, ts)


def test_generate_site_lut_tile_count_le_coverage(kmob_z14_lut: SiteLutResult) -> None:
    all_tiles = tiles_in_coverage(KMOB, zoom=10)
    assert kmob_z14_lut.tile_index.shape[0] <= len(all_tiles)


def test_generate_site_lut_center_tile_small_range(kmob_z14_lut: SiteLutResult) -> None:
    """A tile close to KMOB should have small median range_idx in its mask area."""
    # Find the tile with the smallest max range_idx (closest to radar)
    ts = kmob_z14_lut.range_idx.shape[1]
    mid = ts // 2
    # Among tiles with the smallest non-zero range value at their center pixel
    centers = kmob_z14_lut.range_idx[:, mid, mid]
    masked_centers = np.where(kmob_z14_lut.mask[:, mid, mid] == 1, centers, 65535)
    closest_tile_idx = int(masked_centers.argmin())
    min_center_range = int(centers[closest_tile_idx])
    assert min_center_range < 200, f"Closest tile center range_idx {min_center_range} is unexpectedly large"


def test_generate_site_lut_z8_has_weights(kmob_z8_lut: SiteLutResult) -> None:
    assert kmob_z8_lut.weights is not None
    assert kmob_z8_lut.weights.dtype == np.float32
    assert kmob_z8_lut.weights.shape == kmob_z8_lut.range_idx.shape


def test_generate_site_lut_z14_no_weights(kmob_z14_lut: SiteLutResult) -> None:
    assert kmob_z14_lut.weights is None


def test_generate_site_lut_mask_in_coverage_has_nonzero(kmob_z14_lut: SiteLutResult) -> None:
    for i in range(kmob_z14_lut.tile_index.shape[0]):
        assert kmob_z14_lut.mask[i].sum() > 0, f"Tile {i} has all-zero mask (should have been filtered)"
