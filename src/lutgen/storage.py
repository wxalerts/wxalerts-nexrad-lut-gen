from __future__ import annotations

import io
from typing import Literal
from urllib.parse import urlparse

import boto3
import numpy as np
from botocore.config import Config as BotocoreConfig

from lutgen.config import Config
from lutgen.sites import Site


class LutStorage:
    """Writes .npz files to local disk and optionally to MinIO/S3."""

    def __init__(self, config: Config) -> None:
        self._local_dir = config.output_local_dir
        self._s3 = None
        self._bucket = ""
        self._prefix = ""

        if config.output_minio_url:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=config.minio_endpoint_url,
                aws_access_key_id=config.minio_access_key,
                aws_secret_access_key=config.minio_secret_key,
                region_name=config.minio_region,
                config=BotocoreConfig(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                ),
            )
            parsed = urlparse(config.output_minio_url)
            self._bucket = parsed.netloc
            self._prefix = parsed.path.lstrip("/")

    # ── internal helpers ──────────────────────────────────────────────────────

    def _site_relpath(self, site: Site, zoom: int) -> str:
        return f"{site.icao}/z{zoom:02d}.npz"

    def _mosaic_relpath(self, zoom: int, part: int) -> str:
        if part == 0:
            return f"mosaic/z{zoom:02d}.npz"
        return f"mosaic/z{zoom:02d}_part{part:02d}.npz"

    def _write_local(self, relpath: str, arrays: dict[str, np.ndarray]) -> None:
        full = self._local_dir / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(full), **arrays)  # type: ignore[arg-type]

    def _write_s3(self, relpath: str, arrays: dict[str, np.ndarray]) -> None:
        if self._s3 is None:
            return
        buf = io.BytesIO()
        np.savez_compressed(buf, **arrays)  # type: ignore[arg-type]
        buf.seek(0)
        key = f"{self._prefix}{relpath}" if self._prefix else relpath
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=buf)

    # ── public API ────────────────────────────────────────────────────────────

    def write_site_lut(self, site: Site, zoom: int, arrays: dict[str, np.ndarray]) -> None:
        relpath = self._site_relpath(site, zoom)
        self._write_local(relpath, arrays)
        self._write_s3(relpath, arrays)

    def write_mosaic_lut(self, zoom: int, part: int, arrays: dict[str, np.ndarray]) -> None:
        relpath = self._mosaic_relpath(zoom, part)
        self._write_local(relpath, arrays)
        self._write_s3(relpath, arrays)

    def exists(
        self,
        kind: Literal["site", "mosaic"],
        *,
        site: Site | None = None,
        zoom: int = 0,
        part: int = 0,
    ) -> bool:
        if kind == "site":
            assert site is not None
            relpath = self._site_relpath(site, zoom)
        else:
            relpath = self._mosaic_relpath(zoom, part)
        return (self._local_dir / relpath).exists()
