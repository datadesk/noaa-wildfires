"""Tests that call NOAA's real website.

They are skipped unless you ask for them with ``make test-live`` (or
``uv run pytest -m live``), because they are slow and fail whenever NOAA is
down.
"""

import pytest

import noaa_wildfires

pytestmark = pytest.mark.live


def test_live_fires():
    """Download the latest fires."""
    data = noaa_wildfires.get_hms_fires()
    assert data["features"]


def test_live_smoke():
    """Download the latest smoke."""
    data = noaa_wildfires.get_hms_smoke()
    assert data["features"]


def test_live_records():
    """Every row NOAA publishes right now can be read as a typed record."""
    for fire in noaa_wildfires.get_hms_fire_records():
        assert fire.observed_at.tzinfo is not None
    for smoke in noaa_wildfires.get_hms_smoke_records():
        assert smoke.end >= smoke.start
