from __future__ import annotations

import numpy as np
import pytest

from lutgen.config import Config
from lutgen.site_lut import SiteLutResult
from lutgen.storage import LutStorage
from tests.conftest import KMOB


@pytest.fixture
def tmp_config(tmp_path):
    return Config(output_local_dir=tmp_path)


def test_write_site_lut_creates_file(kmob_z14_lut: SiteLutResult, tmp_config, tmp_path) -> None:
    storage = LutStorage(tmp_config)
    storage.write_site_lut(KMOB, 14, kmob_z14_lut.to_npz_dict())
    assert (tmp_path / "sites" / "KMOB" / "z14.npz").exists()


def test_write_site_lut_loadable(kmob_z14_lut: SiteLutResult, tmp_config, tmp_path) -> None:
    storage = LutStorage(tmp_config)
    storage.write_site_lut(KMOB, 14, kmob_z14_lut.to_npz_dict())
    loaded = np.load(str(tmp_path / "sites" / "KMOB" / "z14.npz"))
    assert "tile_index" in loaded.files
    assert "range_idx" in loaded.files
    assert "azimuth_idx" in loaded.files
    assert "mask" in loaded.files


def test_exists_returns_false_before_write(tmp_config) -> None:
    storage = LutStorage(tmp_config)
    assert not storage.exists("site", site=KMOB, zoom=14)


def test_exists_returns_true_after_write(kmob_z14_lut: SiteLutResult, tmp_config) -> None:
    storage = LutStorage(tmp_config)
    storage.write_site_lut(KMOB, 14, kmob_z14_lut.to_npz_dict())
    assert storage.exists("site", site=KMOB, zoom=14)


def test_write_mosaic_lut_creates_file(mosaic_z6_lut, tmp_config, tmp_path) -> None:
    storage = LutStorage(tmp_config)
    storage.write_mosaic_lut(4, 0, mosaic_z6_lut.to_npz_dict())
    assert (tmp_path / "mosaic" / "z04.npz").exists()


@pytest.mark.parametrize("part", [0, 1])
def test_mosaic_part_naming(mosaic_z6_lut, tmp_config, tmp_path, part) -> None:
    storage = LutStorage(tmp_config)
    storage.write_mosaic_lut(4, part, mosaic_z6_lut.to_npz_dict())
    expected = tmp_path / "mosaic" / ("z04.npz" if part == 0 else "z04_part01.npz")
    assert expected.exists()


def test_write_site_lut_to_s3(kmob_z14_lut: SiteLutResult, tmp_path) -> None:
    """Smoke-test S3 write using moto."""
    pytest.importorskip("boto3")
    pytest.importorskip("moto")

    import os

    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

    import boto3 as b3
    from moto import mock_aws

    with mock_aws():
        b3.client("s3", region_name="us-east-1").create_bucket(Bucket="nexrad-luts")

        config = Config(
            output_local_dir=tmp_path,
            output_minio_url="s3://nexrad-luts/",
            minio_endpoint_url="https://s3.amazonaws.com",  # moto intercepts all S3 calls
            minio_access_key="testing",
            minio_secret_key="testing",
        )
        storage = LutStorage(config)
        storage.write_site_lut(KMOB, 14, kmob_z14_lut.to_npz_dict())

        s3 = b3.client("s3", region_name="us-east-1")
        objs = s3.list_objects_v2(Bucket="nexrad-luts", Prefix="sites/KMOB/")
        assert objs["KeyCount"] >= 1
