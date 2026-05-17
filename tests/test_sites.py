from __future__ import annotations

import re

from lutgen.sites import SITES


def test_all_sites_valid_lat():
    for s in SITES:
        assert -90 <= s.lat <= 90, f"{s.icao}: invalid lat {s.lat}"


def test_all_sites_valid_lon():
    for s in SITES:
        assert -180 <= s.lon <= 180, f"{s.icao}: invalid lon {s.lon}"


def test_all_icao_codes_format():
    pattern = re.compile(r"^[A-Z]{4}$")
    for s in SITES:
        assert pattern.match(s.icao), f"Invalid ICAO code: {s.icao!r}"


def test_no_duplicate_icao_codes():
    icaos = [s.icao for s in SITES]
    dupes = [icao for icao in set(icaos) if icaos.count(icao) > 1]
    assert not dupes, f"Duplicate ICAO codes: {dupes}"


def test_all_sites_have_site_type():
    for s in SITES:
        assert s.site_type in ("wsr88d", "tdwr"), f"{s.icao}: invalid site_type {s.site_type!r}"


def test_site_count_reasonable():
    """Sanity-check: we have at least 150 sites."""
    assert len(SITES) >= 150, f"Expected >= 150 sites, got {len(SITES)}"


def test_wsr88d_n_azimuths():
    for s in SITES:
        if s.site_type == "wsr88d":
            assert s.n_azimuths == 720, f"{s.icao}: WSR-88D should have 720 azimuths"


def test_tdwr_n_azimuths():
    for s in SITES:
        if s.site_type == "tdwr":
            assert s.n_azimuths == 360, f"{s.icao}: TDWR should have 360 azimuths"
