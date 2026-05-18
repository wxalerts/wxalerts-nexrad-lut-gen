from __future__ import annotations

from dataclasses import dataclass

import mercantile
import numpy as np
import pyproj

from lutgen.geometry import haversine_dist, pixel_to_polar
from lutgen.sites import Site
from lutgen.tiles import tile_pixel_lonlat, tiles_in_coverage

_WEBMERC_TO_WGS84 = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

# Tiles per haversine call. float32 grids keep peak RAM at ~8 MB/batch,
# so many threads can run concurrently without OOM.
_TILE_BATCH = 16


@dataclass
class SiteLutResult:
    tile_index: np.ndarray   # int32 (n_tiles, 2)
    range_idx: np.ndarray    # uint16 (n_tiles, H, W)
    azimuth_idx: np.ndarray  # uint16 (n_tiles, H, W)
    mask: np.ndarray         # uint8  (n_tiles, H, W)
    weights: np.ndarray | None = None  # float32 (n_tiles, H, W), only z8-9

    def to_npz_dict(self) -> dict[str, np.ndarray]:
        d: dict[str, np.ndarray] = {
            "tile_index": self.tile_index,
            "range_idx": self.range_idx,
            "azimuth_idx": self.azimuth_idx,
            "mask": self.mask,
        }
        if self.weights is not None:
            d["weights"] = self.weights
        return d


def _compute_weights(
    site: Site,
    tile: mercantile.Tile,
    tile_size: int,
    supersample: int = 4,
) -> np.ndarray:
    """4× supersample weight computation for zoom 8-9 tiles.

    For each output pixel, samples a supersample×supersample sub-pixel grid and
    returns the fraction of sub-pixels that fall into the dominant (range, azimuth)
    cell. Uses pyproj for vectorized Web Mercator → WGS84 unprojection.
    """
    sub = supersample
    n = sub * sub
    bounds = mercantile.xy_bounds(tile)
    x_step = (bounds.right - bounds.left) / tile_size
    y_step = (bounds.top - bounds.bottom) / tile_size

    # Sub-pixel offsets within one output pixel (fractional)
    offs = (np.arange(sub) + 0.5) / sub

    xs_base = bounds.left + np.arange(tile_size) * x_step  # (tile_size,)
    ys_base = bounds.top - np.arange(tile_size) * y_step   # (tile_size,)

    # Expand to (tile_size * sub,) for each axis
    sub_xs = (xs_base[:, None] + offs * x_step).ravel()  # (tile_size*sub,)
    sub_ys = (ys_base[:, None] - offs * y_step).ravel()  # (tile_size*sub,)

    # Full (tile_size*sub) × (tile_size*sub) grid
    xv, yv = np.meshgrid(sub_xs, sub_ys)
    sub_lon, sub_lat = _WEBMERC_TO_WGS84.transform(xv.ravel(), yv.ravel())
    sub_lon = sub_lon.reshape(tile_size * sub, tile_size * sub)
    sub_lat = sub_lat.reshape(tile_size * sub, tile_size * sub)

    sub_range_idx, sub_az_idx, sub_mask = pixel_to_polar(site, sub_lat, sub_lon)

    # Pack (range, az) into a single int64 key; -1 = out-of-coverage
    key = sub_range_idx.astype(np.int64) * 65536 + sub_az_idx.astype(np.int64)
    key[sub_mask == 0] = -1

    # Reshape to (tile_size, tile_size, n) — n = sub*sub sub-pixels per output pixel
    # Original layout: (row_pix * sub, col_pix * sub) → transpose sub dims inward
    key_r = (
        key.reshape(tile_size, sub, tile_size, sub)
           .transpose(0, 2, 1, 3)
           .reshape(tile_size, tile_size, n)
    )

    # Pairwise equality across sub-pixels: (H, W, n, n) → count per pixel → max.
    max_count = (key_r[:, :, :, None] == key_r[:, :, None, :]).sum(axis=-1).max(axis=-1)

    weights = (max_count / n).astype(np.float32)
    # Zero out fully-masked pixels
    weights[np.all(key_r < 0, axis=-1)] = 0.0
    return weights


def _prefilter_tiles(
    site: Site, tiles: list[mercantile.Tile]
) -> list[mercantile.Tile]:
    """Drop tiles whose nearest corner to the site is beyond max_range_m."""
    if not tiles:
        return tiles

    bounds_arr = np.array(
        [(b.west, b.south, b.east, b.north) for b in (mercantile.bounds(t) for t in tiles)]
    )
    nearest_lon = np.clip(site.lon, bounds_arr[:, 0], bounds_arr[:, 2])
    nearest_lat = np.clip(site.lat, bounds_arr[:, 1], bounds_arr[:, 3])

    dist = haversine_dist(site.lat, site.lon, nearest_lat, nearest_lon)
    return [t for t, d in zip(tiles, dist, strict=True) if d <= site.max_range_m]


def _process_batch(
    site: Site,
    batch: list[mercantile.Tile],
    tile_size: int,
) -> tuple[list[mercantile.Tile], np.ndarray, np.ndarray, np.ndarray]:
    """Build float32 lon/lat grids for a tile batch and run haversine pixel_to_polar.

    Using float32 halves intermediate memory vs float64. pixel_to_polar preserves
    the dtype, so all trig stays in float32. numpy ufuncs release the GIL, so
    multiple threads calling this concurrently do run in parallel.
    """
    nb = len(batch)
    lons = np.empty((nb, tile_size, tile_size), dtype=np.float32)
    lats = np.empty((nb, tile_size, tile_size), dtype=np.float32)
    for j, tile in enumerate(batch):
        lon, lat = tile_pixel_lonlat(tile, tile_size)
        lons[j] = lon
        lats[j] = lat
    r_idx, az_idx, msk = pixel_to_polar(site, lats, lons)
    return batch, r_idx, az_idx, msk


def generate_site_lut(
    site: Site,
    zoom: int,
    tile_size: int = 256,
) -> SiteLutResult:
    """Generate the per-site LUT for one (site, zoom) combination."""
    all_tiles = tiles_in_coverage(site, zoom)
    tiles = _prefilter_tiles(site, all_tiles)

    batches = [tiles[i : i + _TILE_BATCH] for i in range(0, len(tiles), _TILE_BATCH)]
    batch_results = [_process_batch(site, b, tile_size) for b in batches]

    tile_indices: list[tuple[int, int]] = []
    range_arrays: list[np.ndarray] = []
    azimuth_arrays: list[np.ndarray] = []
    mask_arrays: list[np.ndarray] = []
    weight_arrays: list[np.ndarray] = []
    compute_weights = zoom in (8, 9)

    for batch, r_idx, az_idx, msk in batch_results:
        for j, tile in enumerate(batch):
            if not msk[j].any():
                continue
            tile_indices.append((tile.x, tile.y))
            range_arrays.append(r_idx[j])
            azimuth_arrays.append(az_idx[j])
            mask_arrays.append(msk[j])
            if compute_weights:
                weight_arrays.append(_compute_weights(site, tile, tile_size))

    if not tile_indices:
        empty = np.zeros((0, tile_size, tile_size), dtype=np.uint16)
        return SiteLutResult(
            tile_index=np.zeros((0, 2), dtype=np.int32),
            range_idx=empty,
            azimuth_idx=empty,
            mask=np.zeros((0, tile_size, tile_size), dtype=np.uint8),
        )

    return SiteLutResult(
        tile_index=np.array(tile_indices, dtype=np.int32),
        range_idx=np.stack(range_arrays),
        azimuth_idx=np.stack(azimuth_arrays),
        mask=np.stack(mask_arrays),
        weights=np.stack(weight_arrays) if compute_weights else None,
    )
