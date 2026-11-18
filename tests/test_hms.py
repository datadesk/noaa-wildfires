"""Offline tests of the download functions and the command line, using saved samples."""

import datetime
import json

import geojson
import pytest
from click.testing import CliRunner

import noaa_wildfires
from noaa_wildfires.cli import cmd


def test_fires_fall_back_to_the_latest_day(fake_noaa):
    """Today has no fire file in the samples, so the 17th is used."""
    data = noaa_wildfires.get_hms_fires()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 7
    assert [u[-12:] for u in fake_noaa.urls] == [
        "20261118.txt",
        "20261117.txt",
    ]


def test_fire_properties_use_noaas_names(fake_noaa):
    """Properties use the column names NOAA's file has now."""
    first = noaa_wildfires.get_hms_fires()["features"][0]
    assert first["geometry"] == {
        "type": "Point",
        "coordinates": [-81.140587, 42.939484],
    }
    assert first["properties"] == {
        "Lon": "-81.140587",
        "Lat": "42.939484",
        "YearDay": "2026321",
        "Time": "0617",
        "Satellite": "NOAA 20",
        "Method": "VIIRS",
        "Ecosystem": "55",
        "FRP": "1.620",
    }


def test_fires_for_a_date(fake_noaa):
    """A date, as text or as a date, reads exactly that day."""
    one = noaa_wildfires.get_hms_fires("2026-11-17")
    two = noaa_wildfires.get_hms_fires(datetime.date(2026, 11, 17))
    assert one == two
    assert all(u.endswith("hms_fire20261117.txt") for u in fake_noaa.urls)


def test_missing_date_is_an_error(fake_noaa):
    """A day with no file raises a clear error instead of reading another day."""
    with pytest.raises(ValueError, match="no fire file for 2026-11-10"):
        noaa_wildfires.get_hms_fires("2026-11-10")


def test_nothing_recent_is_an_error(fake_noaa, monkeypatch):
    """When no recent day has a file, say so."""
    monkeypatch.setattr(noaa_wildfires, "_today", lambda: datetime.date(2026, 12, 25))
    with pytest.raises(ValueError, match="no fire detections"):
        noaa_wildfires.get_hms_fires()
    assert len(fake_noaa.urls) == 4


def test_smoke_skips_an_empty_day(fake_noaa):
    """Today's smoke file has no polygons yet, so the 17th is used."""
    data = noaa_wildfires.get_hms_smoke()
    assert len(data["features"]) == 3
    assert data["features"][0]["geometry"]["type"] == "Polygon"
    assert [u[-12:] for u in fake_noaa.urls] == ["20261118.zip", "20261117.zip"]


def test_smoke_for_an_empty_day(fake_noaa):
    """Asking for an empty day gives an empty collection."""
    assert noaa_wildfires.get_hms_smoke("2026-11-18")["features"] == []


def test_server_error_is_raised(monkeypatch, fake_noaa):
    """Anything other than a file or "not found" is an error."""
    import requests

    from .conftest import FakeResponse

    monkeypatch.setattr(
        noaa_wildfires.requests, "get", lambda url: FakeResponse(status_code=503)
    )
    with pytest.raises(requests.HTTPError):
        noaa_wildfires.get_hms_fires()


def test_urls():
    """The addresses follow NOAA's folder layout."""
    day = datetime.date(2026, 1, 5)
    assert noaa_wildfires.fire_url(day).endswith(
        "/Fire_Points/Text/2026/01/hms_fire20260105.txt"
    )
    assert noaa_wildfires.smoke_url(day).endswith(
        "/Smoke_Polygons/Shapefile/2026/01/hms_smoke20260105.zip"
    )


def test_fires_command(fake_noaa):
    """The command prints GeoJSON."""
    result = CliRunner().invoke(cmd, ["hms-fires"])
    assert result.exit_code == 0
    assert len(geojson.loads(result.output)["features"]) == 7


def test_smoke_command(fake_noaa):
    """The command prints GeoJSON."""
    result = CliRunner().invoke(cmd, ["hms-smoke"])
    assert result.exit_code == 0
    assert len(json.loads(result.output)["features"]) == 3


def test_date_option(fake_noaa):
    """The --date option picks the day."""
    result = CliRunner().invoke(cmd, ["hms-fires", "--date", "2026-11-17"])
    assert result.exit_code == 0
    assert fake_noaa.urls[0].endswith("hms_fire20261117.txt")
