#!/usr/bin/env python3
"""Visualize a LUT .npz file as a side-by-side image.

Usage:
    python scripts/visualize_lut.py /opt/nexrad-luts/sites/KMOB/z14.npz --tile 0
    python scripts/visualize_lut.py /opt/nexrad-luts/sites/KMOB/z14.npz --tile 0 --out kmob_z14.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def normalize(arr: np.ndarray) -> np.ndarray:
    """Scale array to [0, 1] float32."""
    a = arr.astype(np.float32)
    lo, hi = a.min(), a.max()
    if hi == lo:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)


def main() -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lut_file", type=Path)
    parser.add_argument("--tile", type=int, default=0, help="Tile index to render")
    parser.add_argument("--out", type=Path, default=None, help="Output PNG path")
    args = parser.parse_args()

    if not args.lut_file.exists():
        print(f"File not found: {args.lut_file}", file=sys.stderr)
        sys.exit(1)

    data = np.load(str(args.lut_file))
    keys = set(data.files)
    print(f"Keys: {sorted(keys)}")

    if "range_idx" not in keys:
        print("Not a per-site LUT (no range_idx key)", file=sys.stderr)
        sys.exit(1)

    n_tiles = data["tile_index"].shape[0]
    tile_idx = args.tile
    if tile_idx >= n_tiles:
        print(f"--tile {tile_idx} out of range, LUT has {n_tiles} tiles")
        sys.exit(1)

    range_img = normalize(data["range_idx"][tile_idx])
    azimuth_img = normalize(data["azimuth_idx"][tile_idx])
    mask_img = data["mask"][tile_idx].astype(np.float32)

    tx, ty = data["tile_index"][tile_idx]
    title = f"{args.lut_file.name}  tile[{tile_idx}] = ({tx}, {ty})"

    has_weights = "weights" in keys
    n_cols = 4 if has_weights else 3
    fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 4))
    fig.suptitle(title, fontsize=10)

    axes[0].imshow(range_img, cmap="viridis", vmin=0, vmax=1)
    axes[0].set_title("range_idx (normalized)")
    axes[0].axis("off")

    axes[1].imshow(azimuth_img, cmap="hsv", vmin=0, vmax=1)
    axes[1].set_title("azimuth_idx (normalized)")
    axes[1].axis("off")

    axes[2].imshow(mask_img, cmap="gray", vmin=0, vmax=1)
    axes[2].set_title("mask")
    axes[2].axis("off")

    if has_weights:
        axes[3].imshow(normalize(data["weights"][tile_idx]), cmap="plasma")
        axes[3].set_title("weights")
        axes[3].axis("off")

    plt.tight_layout()

    if args.out:
        plt.savefig(str(args.out), dpi=150, bbox_inches="tight")
        print(f"Saved to {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
