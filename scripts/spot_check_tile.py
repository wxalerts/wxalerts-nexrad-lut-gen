#!/usr/bin/env python3
"""Spot-check a single map tile by rendering it from a LUT + polar.zarr.

Usage:
    python scripts/spot_check_tile.py \
        --lut-file s3://nexrad-lut/sites/KABR/z12.npz \
        --polar-zarr s3://nexrad-data/KABR/202605171420/polar.zarr \
        --minio-endpoint http://172.16.50.116:9000 \
        --minio-access-key KEY \
        --minio-secret-key SECRET \
        --product reflectivity --tilt base \
        --output /tmp/spot-check.png \
        [--tile-x 261 --tile-y 421] \
        [--basemap /tmp/spot-check-basemap.png] \
        [--list-good-tiles 10] \
        [--require-stormy]
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse


# ── NWS reflectivity colormap ─────────────────────────────────────────────────

# (lower_dbz_bound, R, G, B, A)
_NWS_REFL_STOPS = [
    (5,  0,   255, 255, 255),   # light cyan
    (10, 0,   200, 255, 255),   # cyan
    (15, 0,   0,   255, 255),   # blue
    (20, 0,   100, 200, 255),   # green-blue
    (25, 0,   200, 0,   255),   # green
    (30, 100, 220, 0,   255),   # yellow-green
    (35, 200, 220, 0,   255),   # yellow
    (40, 255, 150, 0,   255),   # orange
    (45, 255, 0,   0,   255),   # red
    (50, 180, 0,   0,   255),   # dark red
    (55, 220, 0,   220, 255),   # magenta
    (60, 180, 0,   180, 255),   # light purple
    (65, 255, 255, 255, 255),   # white
    (70, 150, 150, 150, 255),   # grey
]

# Fallback NEXRAD ICD scaling when zarr attrs are absent.
# Per NEXRAD ICD, raw byte 0 = below-threshold / no echo,
# raw byte 255 = range folded or no data. These are sentinels, not reflectivity values.
_ICD_SCALE: dict[str, tuple[float, float]] = {
    "reflectivity":              (0.5,      -33.0),
    "velocity":                  (0.01,       0.0),
    "spectrum_width":            (0.5,      -63.5),
    "differential_reflectivity": (0.0625,   -7.875),
    "differential_phase":        (0.043945, -360.0),
}


def _apply_nws_reflectivity(physical: "np.ndarray", valid: "np.ndarray") -> "np.ndarray":
    """Colorize physical dBZ values at pixels where valid is True. RGBA uint8."""
    import numpy as np

    h, w = physical.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    bins = [s[0] for s in _NWS_REFL_STOPS]
    colors = np.array([[s[1], s[2], s[3], s[4]] for s in _NWS_REFL_STOPS], dtype=np.uint8)

    idx = np.digitize(physical, bins) - 1  # -1 → below lowest stop (transparent)
    in_range = (idx >= 0) & valid

    idx_clamped = np.clip(idx, 0, len(colors) - 1)
    rgba[in_range] = colors[idx_clamped[in_range]]

    return rgba


# ── S3/MinIO helpers ──────────────────────────────────────────────────────────

def _make_s3fs(endpoint: str, access_key: str, secret_key: str):
    import s3fs
    return s3fs.S3FileSystem(
        anon=False,
        key=access_key,
        secret=secret_key,
        endpoint_url=endpoint,
        use_ssl=endpoint.startswith("https"),
    )


def _load_lut_npz(lut_path: str, endpoint: str, access_key: str, secret_key: str):
    """Load a .npz LUT from a local path or s3:// URI."""
    import io
    import numpy as np

    if lut_path.startswith("s3://"):
        fs = _make_s3fs(endpoint, access_key, secret_key)
        parsed = urlparse(lut_path)
        s3_path = parsed.netloc + parsed.path
        try:
            with fs.open(s3_path, "rb") as f:
                data = np.load(io.BytesIO(f.read()))
        except Exception as exc:
            print(f"ERROR: could not open LUT from {lut_path}: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        from pathlib import Path
        p = Path(lut_path)
        if not p.exists():
            print(f"ERROR: LUT file not found: {lut_path}", file=sys.stderr)
            sys.exit(1)
        data = np.load(str(p))

    required = {"tile_index", "range_idx", "azimuth_idx", "mask"}
    missing = required - set(data.files)
    if missing:
        print(f"ERROR: LUT missing keys: {missing}", file=sys.stderr)
        sys.exit(1)

    return data


def _open_zarr(zarr_uri: str, endpoint: str, access_key: str, secret_key: str):
    import zarr

    try:
        if zarr_uri.startswith("s3://"):
            root = zarr.open(
                zarr_uri,
                mode="r",
                storage_options={
                    "anon": False,
                    "key": access_key,
                    "secret": secret_key,
                    "endpoint_url": endpoint,
                    "use_ssl": endpoint.startswith("https"),
                },
            )
        else:
            root = zarr.open(zarr_uri, mode="r")
    except Exception as exc:
        print(f"ERROR: could not open zarr at {zarr_uri}: {exc}", file=sys.stderr)
        sys.exit(1)

    return root


# ── tilt resolution ───────────────────────────────────────────────────────────

def _resolve_tilt(root, tilt_selector: str):
    tilt_groups = sorted(
        [k for k in root.keys() if k.startswith("tilt_")],
        key=lambda k: int(k.split("_")[1]),
    )
    if not tilt_groups:
        print("ERROR: no tilt_NN groups found in zarr", file=sys.stderr)
        sys.exit(1)

    elevations = []
    for tg in tilt_groups:
        attrs = dict(root[tg].attrs)
        elevations.append(float(attrs.get("elevation_deg", float("nan"))))

    if tilt_selector == "base":
        best_idx = int(min(range(len(elevations)), key=lambda i: elevations[i]))
    elif tilt_selector.lstrip("-").replace(".", "", 1).isdigit() and "." in tilt_selector:
        target = float(tilt_selector)
        best_idx = int(min(range(len(elevations)), key=lambda i: abs(elevations[i] - target)))
    elif tilt_selector.isdigit():
        name = f"tilt_{int(tilt_selector):02d}"
        if name not in tilt_groups:
            print(
                f"ERROR: {name} not in zarr. Available: {tilt_groups}", file=sys.stderr
            )
            sys.exit(1)
        best_idx = tilt_groups.index(name)
    else:
        print(
            f"ERROR: cannot parse --tilt '{tilt_selector}'. "
            "Use 'base', a float (elevation degrees), or an int (tilt index).",
            file=sys.stderr,
        )
        sys.exit(1)

    selected = tilt_groups[best_idx]
    print(f"Selected {selected} with elevation {elevations[best_idx]:.1f}°")
    return root[selected], selected


# ── sentinel-aware tile scanning ──────────────────────────────────────────────

def _scan_tiles(
    full_ref: "np.ndarray",
    azimuth_idx: "np.ndarray",
    range_idx: "np.ndarray",
    mask: "np.ndarray",
    tile_index: "np.ndarray",
    scale_factor: float,
    add_offset: float,
) -> list[dict]:
    """Compute sentinel-aware per-tile statistics.

    Excludes raw == 0 (no echo) and raw == 255 (missing/range-folded) from
    "real data." Returns list of dicts sorted by mean_real descending. Tiles
    with zero mask coverage are omitted.
    """
    import numpy as np

    candidates = []
    n_tiles = tile_index.shape[0]

    for r in range(n_tiles):
        in_mask = mask[r] > 0
        n_total = int(in_mask.sum())
        if n_total == 0:
            continue

        raw_r = full_ref[azimuth_idx[r], range_idx[r]]

        n_sentinel_0   = int(((raw_r == 0)   & in_mask).sum())
        n_sentinel_255 = int(((raw_r == 255) & in_mask).sum())
        real_mask = (raw_r >= 1) & (raw_r <= 254) & in_mask
        n_real = int(real_mask.sum())

        if n_real > 0:
            mean_real     = float(raw_r[real_mask].mean())
            mean_real_dbz = mean_real * scale_factor + add_offset
        else:
            mean_real     = 0.0
            mean_real_dbz = float("nan")

        candidates.append({
            "row":            r,
            "xy":             (int(tile_index[r, 0]), int(tile_index[r, 1])),
            "n_total":        n_total,
            "n_real":         n_real,
            "n_sentinel_0":   n_sentinel_0,
            "n_sentinel_255": n_sentinel_255,
            "mean_real":      mean_real,
            "mean_real_dbz":  mean_real_dbz,
        })

    candidates.sort(key=lambda x: -x["mean_real"])
    return candidates


def _print_candidates_table(candidates: list[dict], n: int) -> None:
    header = f"  {'tile (x,y)':>20}  {'real%':>6}  {'zero%':>6}  {'255%':>6}  {'mean dBZ':>9}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for c in candidates[:n]:
        xy      = c["xy"]
        n_total = c["n_total"]
        real_pct = 100 * c["n_real"]         / n_total
        zero_pct = 100 * c["n_sentinel_0"]   / n_total
        s255_pct = 100 * c["n_sentinel_255"] / n_total
        dbz_str  = f"{c['mean_real_dbz']:.1f}" if c["n_real"] > 0 else "  n/a"
        print(f"  {str(xy):>20}  {real_pct:>5.1f}%  {zero_pct:>5.1f}%  {s255_pct:>5.1f}%  {dbz_str:>9}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a single map tile from a LUT + polar.zarr for validation."
    )
    parser.add_argument("--lut-file", required=True, help="Path or s3:// URI to .npz LUT")
    parser.add_argument("--polar-zarr", required=True, help="s3:// URI or local path to polar.zarr")
    parser.add_argument("--minio-endpoint", default="http://localhost:9000")
    parser.add_argument("--minio-access-key", default="minioadmin")
    parser.add_argument("--minio-secret-key", default="minioadmin")
    parser.add_argument("--tile-x", type=int, default=None)
    parser.add_argument("--tile-y", type=int, default=None)
    parser.add_argument("--product", default="reflectivity")
    parser.add_argument("--tilt", default="base", help="'base', a float elevation, or int index")
    parser.add_argument("--output", default=None, help="Output PNG path (required unless --list-good-tiles)")
    parser.add_argument("--basemap", default=None, help="Optional path to save OSM basemap tile")
    parser.add_argument(
        "--list-good-tiles", type=int, default=None, metavar="N",
        help="Print top N candidate tiles ranked by real-data quality and exit without rendering.",
    )
    parser.add_argument(
        "--require-stormy", action="store_true",
        help=(
            "Exit non-zero if no tile has mean_real > 100 raw (~17 dBZ, drizzle threshold). "
            "Useful for CI runs that need real weather data."
        ),
    )
    args = parser.parse_args()

    if args.list_good_tiles is None and args.output is None:
        print("ERROR: --output is required unless --list-good-tiles is specified", file=sys.stderr)
        sys.exit(1)

    # ── validate deps ─────────────────────────────────────────────────────────
    missing_deps = []
    for mod in ("numpy", "zarr", "s3fs", "PIL", "mercantile"):
        try:
            __import__(mod)
        except ImportError:
            missing_deps.append(mod if mod != "PIL" else "pillow")
    if missing_deps:
        print(
            f"ERROR: missing dependencies: {missing_deps}\n"
            f"  pip install {' '.join(missing_deps)}",
            file=sys.stderr,
        )
        sys.exit(1)

    import numpy as np
    import mercantile
    from PIL import Image

    # ── 1. Load LUT ───────────────────────────────────────────────────────────
    print(f"\n[1/8] Loading LUT from {args.lut_file}")
    lut = _load_lut_npz(args.lut_file, args.minio_endpoint, args.minio_access_key, args.minio_secret_key)

    tile_index  = lut["tile_index"]    # (n_tiles, 2)  int32
    range_idx   = lut["range_idx"]     # (n_tiles, H, W) uint16
    azimuth_idx = lut["azimuth_idx"]   # (n_tiles, H, W) uint16
    mask        = lut["mask"]          # (n_tiles, H, W) uint8
    n_tiles     = tile_index.shape[0]

    import re
    zoom_match = re.search(r"z(\d+)\.npz", args.lut_file)
    zoom = int(zoom_match.group(1)) if zoom_match else 12
    print(f"  {n_tiles} tiles at zoom {zoom}")

    # ── 2. Open polar.zarr ────────────────────────────────────────────────────
    print(f"\n[2/8] Opening polar.zarr: {args.polar_zarr}")
    root = _open_zarr(
        args.polar_zarr, args.minio_endpoint, args.minio_access_key, args.minio_secret_key
    )
    attrs = dict(root.attrs)
    print(
        f"  site_id={attrs.get('site_id')}  vcp={attrs.get('vcp')}  "
        f"total_tilts={attrs.get('total_tilts')}  scan_time_utc={attrs.get('scan_time_utc')}"
    )

    # ── 3. Resolve tilt ───────────────────────────────────────────────────────
    print(f"\n[3/8] Resolving tilt ({args.tilt!r})")
    tilt_group, tilt_name = _resolve_tilt(root, args.tilt)

    # ── 4. Read product array ─────────────────────────────────────────────────
    print(f"\n[4/8] Reading product '{args.product}'")
    available_products = list(tilt_group.keys())
    if args.product not in tilt_group:
        print(
            f"ERROR: product '{args.product}' not in {tilt_name}.\n"
            f"Available: {available_products}",
            file=sys.stderr,
        )
        sys.exit(1)

    product_arr = tilt_group[args.product]
    prod_attrs  = dict(product_arr.attrs)

    # Determine scale/offset — fall back to NEXRAD ICD constants if attrs absent.
    if "scale_factor" in prod_attrs and "add_offset" in prod_attrs:
        scale_factor = float(prod_attrs["scale_factor"])
        add_offset   = float(prod_attrs["add_offset"])
    else:
        scale_factor, add_offset = _ICD_SCALE.get(args.product, (1.0, 0.0))
        print(
            f"  WARNING: scale_factor/add_offset missing from zarr attrs; "
            f"using NEXRAD ICD defaults (scale={scale_factor}, offset={add_offset})"
        )

    print(f"  polar shape={product_arr.shape}  dtype={product_arr.dtype}")
    print(f"  scale_factor={scale_factor}  add_offset={add_offset}")
    print("  Loading full array into memory for tile scanning...")
    full_ref = np.array(product_arr)

    # ── 5. Scan tiles (sentinel-aware) ────────────────────────────────────────
    # Per NEXRAD ICD, raw byte 0 = below-threshold / no echo,
    # raw byte 255 = range folded or no data. These are sentinels, not reflectivity values.
    print(f"\n[5/8] Scanning {n_tiles} tiles for real-data quality")
    candidates = _scan_tiles(
        full_ref, azimuth_idx, range_idx, mask, tile_index, scale_factor, add_offset
    )

    good = [
        c for c in candidates
        if c["n_total"] > 0
        and c["n_real"] / c["n_total"] >= 0.20
        and c["mean_real"] > 70
    ]
    n_with_any_real = sum(1 for c in candidates if c["n_real"] > 0)
    print(
        f"  {n_with_any_real}/{n_tiles} tiles have real data (raw 1–254); "
        f"{len(good)} qualify as good (≥20% real, mean_real>70)"
    )
    print("\n  Top 10 candidate tiles:")
    _print_candidates_table(candidates, 10)

    # ── --list-good-tiles: print and exit ─────────────────────────────────────
    if args.list_good_tiles is not None:
        n = args.list_good_tiles
        print(f"\nTop {n} tiles by real-data quality:")
        _print_candidates_table(candidates, n)
        sys.exit(0)

    # ── --require-stormy ──────────────────────────────────────────────────────
    if args.require_stormy:
        stormy = [c for c in candidates if c["mean_real"] > 100]
        if not stormy:
            print(
                "ERROR: --require-stormy: no tile has mean_real > 100 raw "
                "(~17 dBZ drizzle threshold) — polar.zarr contains no significant weather",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"  --require-stormy: OK ({len(stormy)} tiles above drizzle threshold)")

    # ── Pick tile ─────────────────────────────────────────────────────────────
    if args.tile_x is not None and args.tile_y is not None:
        matches = np.where(
            (tile_index[:, 0] == args.tile_x) & (tile_index[:, 1] == args.tile_y)
        )[0]
        if len(matches) == 0:
            print(
                f"ERROR: tile ({args.tile_x}, {args.tile_y}) not found in LUT.\n"
                f"Available tiles (first 20): {tile_index[:20].tolist()}",
                file=sys.stderr,
            )
            sys.exit(1)
        row = int(matches[0])
        tx, ty = args.tile_x, args.tile_y
        chosen = next((c for c in candidates if c["xy"] == (tx, ty)), None)
        if chosen and chosen["n_total"] > 0:
            real_pct = 100 * chosen["n_real"] / chosen["n_total"]
            dbz_str  = f"{chosen['mean_real_dbz']:.1f}" if chosen["n_real"] > 0 else "n/a"
            print(f"\nUsing specified tile ({tx}, {ty}): {real_pct:.0f}% real data, mean {dbz_str} dBZ")
        else:
            print(f"\nUsing specified tile ({tx}, {ty})")
    else:
        if good:
            chosen = good[0]
        elif candidates:
            print(
                "\nWARNING: no tile qualifies as good for validation "
                "(≥20% real data, mean_real>70); using tile with highest mean_real"
            )
            chosen = candidates[0]
        else:
            print("ERROR: no tiles with any mask coverage in LUT", file=sys.stderr)
            sys.exit(1)
        row = chosen["row"]
        tx, ty = chosen["xy"]
        real_pct = 100 * chosen["n_real"] / chosen["n_total"] if chosen["n_total"] > 0 else 0
        dbz_str  = f"{chosen['mean_real_dbz']:.1f}" if chosen["n_real"] > 0 else "n/a"
        print(f"\nSelected tile ({tx}, {ty}) with {real_pct:.0f}% real data, mean {dbz_str} dBZ")

    tile_range_idx   = range_idx[row]    # (256, 256)
    tile_azimuth_idx = azimuth_idx[row]  # (256, 256)
    tile_mask        = mask[row]         # (256, 256)

    raw = full_ref[tile_azimuth_idx, tile_range_idx]
    print(f"  raw dtype={raw.dtype}  shape={raw.shape}")

    # ── 6. Sentinel-aware decode ──────────────────────────────────────────────
    # Only raw 1–254 encodes actual reflectivity. Raw 0 = no echo; raw 255 = no data.
    print("\n[6/8] Decoding to physical units (sentinel-aware)")
    valid_data = (raw >= 1) & (raw <= 254) & (tile_mask > 0)

    physical = np.full(raw.shape, np.nan, dtype=np.float32)
    physical[valid_data] = raw[valid_data].astype(np.float32) * scale_factor + add_offset

    n_valid   = int(valid_data.sum())
    n_no_echo = int(((raw == 0)   & (tile_mask > 0)).sum())
    n_no_data = int(((raw == 255) & (tile_mask > 0)).sum())
    print(f"  valid: {n_valid}  no-echo (0): {n_no_echo}  no-data (255): {n_no_data}")
    if n_valid > 0:
        print(
            f"  {args.product}: "
            f"min={float(physical[valid_data].min()):.1f}  "
            f"max={float(physical[valid_data].max()):.1f}  "
            f"mean={float(physical[valid_data].mean()):.1f} dBZ"
        )

    # ── 7. Apply colormap ─────────────────────────────────────────────────────
    print("\n[7/8] Applying colormap")
    rgba = _apply_nws_reflectivity(physical, valid_data)

    # ── 8. Save PNG ───────────────────────────────────────────────────────────
    print(f"\n[8/8] Saving PNG to {args.output}")
    Image.fromarray(rgba, mode="RGBA").save(args.output)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n── Summary ─────────────────────────────────────────────────────")
    bounds = mercantile.bounds(mercantile.Tile(x=tx, y=ty, z=zoom))
    print(f"  Tile:                z{zoom}/{tx}/{ty}")
    print(f"  Bounds:              W={bounds.west:.4f} S={bounds.south:.4f} E={bounds.east:.4f} N={bounds.north:.4f}")
    print(f"  In-coverage pixels:  {int(tile_mask.sum())} / {tile_mask.size}")
    print(f"  Real-data pixels:    {n_valid} / {int(tile_mask.sum())}")
    print(f"  Output:              {args.output}")

    # ── optional basemap ──────────────────────────────────────────────────────
    if args.basemap:
        print(f"\n[+] Downloading OSM basemap tile z{zoom}/{tx}/{ty}")
        try:
            import requests
            url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            headers = {"User-Agent": "wxalerts-spot-check/1.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            with open(args.basemap, "wb") as f:
                f.write(resp.content)
            print(f"    Saved basemap to {args.basemap}")
            print("    Open both PNGs side by side to verify geographic alignment.")
        except Exception as exc:
            print(f"    WARNING: could not download basemap: {exc}", file=sys.stderr)

    print("""
╔══════════════════════════════════════════════════════════════╗
║                   VALIDATION CHECKLIST                       ║
╠══════════════════════════════════════════════════════════════╣
║  1. Does the PNG show a radial gradient pattern centered     ║
║     roughly at the radar location?                           ║
║  2. Do dBZ values fall in a sensible range (not all the      ║
║     same value)?                                             ║
║  3. Does the coverage circle (mask boundary) form a clean    ║
║     arc near the tile edges?                                 ║
║  4. If basemap was rendered: do geographic features align?   ║
╚══════════════════════════════════════════════════════════════╝""")


if __name__ == "__main__":
    main()
