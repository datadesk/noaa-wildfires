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
    noaa_wildfires.get_hms_fires()


def test_live_smoke():
    """Download the latest smoke."""
    noaa_wildfires.get_hms_smoke()
