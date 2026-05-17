from __future__ import annotations

from dataclasses import dataclass

import mercantile
import numpy as np

from lutgen.geometry import coverage_bbox_wgs84, pixel_to_polar
from lutgen.sites import SITES
from lutgen.tiles import tile_pixel_lonlat


@dataclass
class MosaicLutResult:
    tile_index: np.ndarray           # int32 (n_tiles, 2)
    contribution_offsets: np.ndarray # int32 (n_tiles + 1,)
    site_ids: np.ndarray             # bytes (n_contributions, 4)
    range_idx: np.ndarray            # uint16 (n_contributions, H, W)
    azimuth_idx: np.ndarray          # uint16 (n_contributions, H, W)
    mask: np.ndarray                 # uint8  (n_contributions, H, W)

    def to_npz_dict(self) -> dict[str, np.ndarray]:
        return {
            "tile_index": self.tile_index,
            "contribution_offsets": self.contribution_offsets,
            "site_ids": self.site_ids,
            "range_idx": self.range_idx,
            "azimuth_idx": self.azimuth_idx,
            "mask": self.mask,
        }


def _tile_bbox(tile: mercantile.Tile) -> tuple[float, float, float, float]:
    b = mercantile.bounds(tile)
    return (b.west, b.south, b.east, b.north)


def _bboxes_intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def generate_mosaic_lut(zoom: int, tile_size: int = 256) -> MosaicLutResult:
    """Generate the mosaic LUT for one zoom level across all sites."""
    site_bboxes = {site.icao: coverage_bbox_wgs84(site) for site in SITES}

    # Collect all tiles that intersect any site's coverage
    all_tiles: set[mercantile.Tile] = set()
    for site in SITES:
        bbox = site_bboxes[site.icao]
        for tile in mercantile.tiles(bbox[0], bbox[1], bbox[2], bbox[3], zooms=zoom):
            all_tiles.add(tile)

    tile_list = sorted(all_tiles, key=lambda t: (t.x, t.y))

    tile_indices: list[tuple[int, int]] = []
    offsets: list[int] = [0]
    site_id_list: list[bytes] = []
    range_list: list[np.ndarray] = []
    azimuth_list: list[np.ndarray] = []
    mask_list: list[np.ndarray] = []

    for tile in tile_list:
        tile_bbox = _tile_bbox(tile)
        candidates = [s for s in SITES if _bboxes_intersect(site_bboxes[s.icao], tile_bbox)]

        lon, lat = tile_pixel_lonlat(tile, tile_size)
        tile_contribs = 0

        for site in candidates:
            range_idx, azimuth_idx, mask = pixel_to_polar(site, lat, lon)
            if mask.sum() == 0:
                continue
            icao_bytes = site.icao.encode("ascii").ljust(4)[:4]
            site_id_list.append(icao_bytes)
            range_list.append(range_idx)
            azimuth_list.append(azimuth_idx)
            mask_list.append(mask)
            tile_contribs += 1

        if tile_contribs == 0:
            continue  # Tile has no actual coverage — omit

        tile_indices.append((tile.x, tile.y))
        offsets.append(offsets[-1] + tile_contribs)

    if not tile_indices:
        empty_u16 = np.zeros((0, tile_size, tile_size), dtype=np.uint16)
        return MosaicLutResult(
            tile_index=np.zeros((0, 2), dtype=np.int32),
            contribution_offsets=np.zeros(1, dtype=np.int32),
            site_ids=np.zeros((0, 4), dtype=np.uint8),
            range_idx=empty_u16,
            azimuth_idx=empty_u16,
            mask=np.zeros((0, tile_size, tile_size), dtype=np.uint8),
        )

    site_ids_array = np.frombuffer(b"".join(site_id_list), dtype=np.uint8).reshape(-1, 4)

    return MosaicLutResult(
        tile_index=np.array(tile_indices, dtype=np.int32),
        contribution_offsets=np.array(offsets, dtype=np.int32),
        site_ids=site_ids_array,
        range_idx=np.stack(range_list),
        azimuth_idx=np.stack(azimuth_list),
        mask=np.stack(mask_list),
    )


def split_mosaic_lut(result: MosaicLutResult, max_bytes: int = 500 * 1024 * 1024) -> list[MosaicLutResult]:
    """Split a MosaicLutResult into parts where each part's contribution arrays
    fit within max_bytes. Used for z8/z9 which can exceed 500 MB per file.
    """
    n_tiles = len(result.tile_index)
    if n_tiles == 0:
        return [result]

    # Estimate bytes per contribution (two uint16 + one uint8 arrays of 256×256)
    tile_size = result.range_idx.shape[1]
    bytes_per_contrib = tile_size * tile_size * (2 + 2 + 1)

    parts: list[MosaicLutResult] = []
    start_tile = 0

    while start_tile < n_tiles:
        end_tile = start_tile
        running_bytes = 0
        while end_tile < n_tiles:
            c_start = result.contribution_offsets[end_tile]
            c_end = result.contribution_offsets[end_tile + 1]
            chunk_bytes = (c_end - c_start) * bytes_per_contrib
            if running_bytes + chunk_bytes > max_bytes and end_tile > start_tile:
                break
            running_bytes += chunk_bytes
            end_tile += 1

        c_lo = result.contribution_offsets[start_tile]
        c_hi = result.contribution_offsets[end_tile]

        new_offsets = result.contribution_offsets[start_tile : end_tile + 1] - c_lo

        parts.append(
            MosaicLutResult(
                tile_index=result.tile_index[start_tile:end_tile],
                contribution_offsets=new_offsets,
                site_ids=result.site_ids[c_lo:c_hi],
                range_idx=result.range_idx[c_lo:c_hi],
                azimuth_idx=result.azimuth_idx[c_lo:c_hi],
                mask=result.mask[c_lo:c_hi],
            )
        )
        start_tile = end_tile

    return parts
