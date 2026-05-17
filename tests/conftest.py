from __future__ import annotations

import pytest

from lutgen.sites import Site

KMOB = Site(
    icao="KMOB",
    name="Mobile, AL",
    lat=30.6794,
    lon=-88.2397,
    elevation_m=63.0,
    site_type="wsr88d",
)

KABR = Site(
    icao="KABR",
    name="Aberdeen, SD",
    lat=45.4558,
    lon=-98.4131,
    elevation_m=397.5,
    site_type="wsr88d",
)

MINI_SITES = [KMOB, KABR]


@pytest.fixture
def kmob() -> Site:
    return KMOB


@pytest.fixture
def kabr() -> Site:
    return KABR


@pytest.fixture
def mini_sites() -> list[Site]:
    return MINI_SITES


@pytest.fixture(scope="session")
def kmob_z14_lut():
    """Session-scoped KMOB z10 LUT used as the standard site-LUT fixture.

    z10 is a valid production zoom (~165 in-coverage tiles) and runs in a few
    seconds, unlike z14 which has ~40k in-coverage tiles and would take many
    minutes in CI.
    """
    from lutgen.site_lut import generate_site_lut
    return generate_site_lut(KMOB, zoom=10)


@pytest.fixture(scope="session")
def kmob_z8_lut():
    """Session-scoped KMOB z8 LUT (small tile_size for speed)."""
    from lutgen.site_lut import generate_site_lut
    return generate_site_lut(KMOB, zoom=8, tile_size=16)


@pytest.fixture(scope="session")
def mosaic_z6_lut():
    """Session-scoped mosaic z6 LUT — computed once, shared across all tests."""
    from lutgen.mosaic_lut import generate_mosaic_lut
    return generate_mosaic_lut(zoom=6)
