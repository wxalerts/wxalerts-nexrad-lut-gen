# wxalerts-nexrad-lut-gen

CLI tool that generates lookup tables (LUTs) mapping Web Mercator tile pixels to NEXRAD polar radar coordinates (range_idx, azimuth_idx). LUTs are purely geometric — generate once, reuse forever.

## Output

**Per-site LUTs** (for PolarRadarReader / rio-tiler):
```
s3://nexrad-luts/sites/<ICAO>/z<NN>.npz
/opt/nexrad-luts/sites/<ICAO>/z<NN>.npz
```

**Mosaic LUTs** (for mosaic worker):
```
s3://nexrad-luts/mosaic/z<NN>.npz          # z4-z7
s3://nexrad-luts/mosaic/z<NN>_part<NN>.npz  # z8-z9 (split at 500 MB)
/opt/nexrad-mosaic-luts/z<NN>.npz
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# One site, one zoom, local only (for testing)
lutgen sites generate --site KMOB --zoom 14 --output-local ./test-luts

# Visualize
python scripts/visualize_lut.py ./test-luts/sites/KMOB/z14.npz --tile 0

# All sites, dual-destination
lutgen sites generate --all --concurrency 8 \
  --output-local /opt/nexrad-luts \
  --output-minio s3://nexrad-luts/

# Mosaic LUTs
lutgen mosaic generate \
  --output-local /opt/nexrad-mosaic-luts \
  --output-minio s3://nexrad-luts/

# List all 160+ embedded sites
lutgen list-sites

# Verify a generated file
lutgen verify /opt/nexrad-luts/sites/KMOB/z14.npz
```

## Configuration

Copy `.env.example` to `.env` and fill in values. All settings can also be passed as environment variables:

| Variable | Default | Description |
|---|---|---|
| `OUTPUT_LOCAL_DIR` | `/opt/nexrad-luts` | Local output directory |
| `OUTPUT_MINIO_URL` | — | S3/MinIO destination (e.g. `s3://nexrad-luts/`) |
| `MINIO_ENDPOINT_URL` | — | Required if `OUTPUT_MINIO_URL` set |
| `MINIO_ACCESS_KEY` | — | Required if `OUTPUT_MINIO_URL` set |
| `MINIO_SECRET_KEY` | — | Required if `OUTPUT_MINIO_URL` set |
| `MINIO_REGION` | `us-east-1` | |
| `LOG_LEVEL` | `INFO` | |

## Docker

```bash
docker run --rm \
  -e OUTPUT_LOCAL_DIR=/luts \
  -e MINIO_ENDPOINT_URL=http://minio:9000 \
  -e MINIO_ACCESS_KEY=... \
  -e MINIO_SECRET_KEY=... \
  -v /opt/nexrad-luts:/luts \
  ghcr.io/wxalerts/wxalerts-nexrad-lut-gen:latest \
  sites generate --all --concurrency 8 --output-minio s3://nexrad-luts/
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check src/ tests/
mypy src/
pytest -v
```
