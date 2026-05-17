from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    output_local_dir: Path = Path("/opt/nexrad-luts")
    output_minio_url: str | None = None
    minio_endpoint_url: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_region: str = "us-east-1"
    log_level: str = "INFO"

    @model_validator(mode="after")
    def check_minio_config(self) -> Config:
        if self.output_minio_url:
            missing = [
                name
                for name, val in [
                    ("MINIO_ENDPOINT_URL", self.minio_endpoint_url),
                    ("MINIO_ACCESS_KEY", self.minio_access_key),
                    ("MINIO_SECRET_KEY", self.minio_secret_key),
                ]
                if not val
            ]
            if missing:
                raise ValueError(
                    f"OUTPUT_MINIO_URL is set but missing: {', '.join(missing)}"
                )
        return self
