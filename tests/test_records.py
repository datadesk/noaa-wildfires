"""Offline tests of the typed records."""

import dataclasses
import doctest
from datetime import UTC, datetime

import pytest

import noaa_wildfires
from noaa_wildfires import HmsFire, HmsSmoke, records


def test_records_doctests():
    """The examples in the records module's docstrings are correct."""
    assert doctest.testmod(records).failed == 0


def test_fire_records(fake_noaa):
    """Numbers are numbers and the time carries its time zone."""
    fires = noaa_wildfires.get_hms_fire_records()
    assert len(fires) == 7
    first = fires[0]
    assert first == HmsFire(
        latitude=42.939484,
        longitude=-81.140587,
        observed_at=datetime(2026, 11, 17, 6, 17, tzinfo=UTC),
        satellite="NOAA 20",
        method="VIIRS",
        ecosystem=55,
        frp=1.62,
    )
    assert {f.satellite for f in fires} == {
        "NOAA 20",
        "NOAA 21",
        "GOES-EAST",
        "GOES-WEST",
    }


def test_missing_frp_is_none(fake_noaa):
    """NOAA's -999 means no measurement, which becomes None."""
    analysis = [
        f for f in noaa_wildfires.get_hms_fire_records() if f.method == "ANALYSIS"
    ]
    assert len(analysis) == 1
    assert analysis[0].frp is None


def test_smoke_records(fake_noaa):
    """Smoke has an outline, two times and a density."""
    smoke = noaa_wildfires.get_hms_smoke_records()
    assert len(smoke) == 3
    assert {s.density for s in smoke} == {"Light", "Medium", "Heavy"}
    first = smoke[0]
    assert first.geometry["type"] == "Polygon"
    assert first.start.tzinfo is UTC
    assert first.end > first.start
    assert first.satellite.startswith("GOES")


def test_records_are_frozen():
    """A record cannot be changed after it is made."""
    smoke = HmsSmoke({}, "GOES-WEST", datetime.now(UTC), datetime.now(UTC), "Light")
    with pytest.raises(dataclasses.FrozenInstanceError):
        smoke.density = "Heavy"  # type: ignore[misc]


def test_bad_rows_are_value_errors():
    """A row that cannot be read raises ValueError with a plain message."""
    with pytest.raises(ValueError, match="no 'FRP' column"):
        HmsFire.from_properties({"Lat": "1"})
    with pytest.raises(ValueError, match="Cannot read the NOAA time"):
        records.parse_noaa_time("2026", "0617")
    with pytest.raises(ValueError):
        HmsFire.from_properties(
            {
                "Lon": "x",
                "Lat": "1",
                "YearDay": "2026321",
                "Time": "0617",
                "Satellite": "a",
                "Method": "b",
                "Ecosystem": "1",
                "FRP": "1",
            }
        )


def test_geojson_values_are_text(fake_noaa):
    """The GeoJSON function gives text values with NOAA's names."""
    properties = noaa_wildfires.get_hms_fires()["features"][0]["properties"]
    assert properties["FRP"] == "1.620"
