from __future__ import annotations

import mercantile
import numpy as np
import pytest

from lutgen.mosaic_lut import MosaicLutResult, split_mosaic_lut


def test_mosaic_lut_z6_nonempty(mosaic_z6_lut: MosaicLutResult) -> None:
    assert mosaic_z6_lut.tile_index.shape[0] > 0


def test_mosaic_lut_z6_central_us_has_contributions(mosaic_z6_lut: MosaicLutResult) -> None:
    """A tile over central US at z6 must have multiple contributing sites."""
    kc_tile = mercantile.tile(-94.0, 39.0, 6)
    matches = np.where(
        (mosaic_z6_lut.tile_index[:, 0] == kc_tile.x)
        & (mosaic_z6_lut.tile_index[:, 1] == kc_tile.y)
    )[0]
    assert len(matches) > 0, "Kansas City z6 tile should be in mosaic LUT"
    tile_i = matches[0]
    n_contrib = mosaic_z6_lut.contribution_offsets[tile_i + 1] - mosaic_z6_lut.contribution_offsets[tile_i]
    assert n_contrib >= 2, f"Expected >= 2 contributing radars, got {n_contrib}"


def test_mosaic_lut_atlantic_tile_absent(mosaic_z6_lut: MosaicLutResult) -> None:
    """A tile over the mid-Atlantic Ocean should be absent."""
    ocean_tile = mercantile.tile(-40.0, 40.0, 6)
    matches = np.where(
        (mosaic_z6_lut.tile_index[:, 0] == ocean_tile.x)
        & (mosaic_z6_lut.tile_index[:, 1] == ocean_tile.y)
    )[0]
    assert len(matches) == 0, "Ocean tile should be absent from mosaic LUT"


def test_mosaic_lut_offsets_monotone(mosaic_z6_lut: MosaicLutResult) -> None:
    offsets = mosaic_z6_lut.contribution_offsets
    assert np.all(np.diff(offsets) >= 0), "contribution_offsets must be non-decreasing"


def test_mosaic_lut_offsets_last_equals_n_contributions(mosaic_z6_lut: MosaicLutResult) -> None:
    assert mosaic_z6_lut.contribution_offsets[-1] == mosaic_z6_lut.range_idx.shape[0]


def test_mosaic_lut_dtypes(mosaic_z6_lut: MosaicLutResult) -> None:
    assert mosaic_z6_lut.tile_index.dtype == np.int32
    assert mosaic_z6_lut.contribution_offsets.dtype == np.int32
    assert mosaic_z6_lut.range_idx.dtype == np.uint16
    assert mosaic_z6_lut.azimuth_idx.dtype == np.uint16
    assert mosaic_z6_lut.mask.dtype == np.uint8


def test_mosaic_lut_site_ids_shape(mosaic_z6_lut: MosaicLutResult) -> None:
    n_contrib = mosaic_z6_lut.range_idx.shape[0]
    assert mosaic_z6_lut.site_ids.shape == (n_contrib, 4)


def test_split_mosaic_lut_preserves_data(mosaic_z6_lut: MosaicLutResult) -> None:
    parts = split_mosaic_lut(mosaic_z6_lut, max_bytes=1024 * 1024)  # 1 MB
    if len(parts) == 1:
        pytest.skip("Result fits in one part at this zoom")
    for part in parts:
        assert part.contribution_offsets[0] == 0
        assert part.contribution_offsets[-1] == part.range_idx.shape[0]
