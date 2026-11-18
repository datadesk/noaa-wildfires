"""Offline tests of the download functions and the command line, using saved samples."""

import json

import geojson
from click.testing import CliRunner

import noaa_wildfires
from noaa_wildfires.cli import cmd


def test_fires(fake_noaa):
    """Each row of the text file becomes a point with the row as its properties."""
    data = noaa_wildfires.get_hms_fires()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 5
    first = data["features"][0]
    assert first["geometry"]["type"] == "Point"
    assert first["geometry"]["coordinates"] == [-68.500916, 18.726505]
    assert first["properties"]["Satellite"] == "SUOMI NPP"
    assert first["properties"]["Fire RadPower"] == "1.150"
    assert len(fake_noaa.urls) == 1


def test_smoke(fake_noaa):
    """The three shapefile pieces are downloaded and turned into polygons."""
    data = noaa_wildfires.get_hms_smoke()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    assert data["features"][0]["geometry"]["type"] == "Polygon"
    assert len(fake_noaa.urls) == 3


def test_fires_command(fake_noaa):
    """The command prints GeoJSON."""
    result = CliRunner().invoke(cmd, ["hms-fires"])
    assert result.exit_code == 0
    assert len(geojson.loads(result.output)["features"]) == 5


def test_smoke_command(fake_noaa):
    """The command prints GeoJSON."""
    result = CliRunner().invoke(cmd, ["hms-smoke"])
    assert result.exit_code == 0
    assert json.loads(result.output)["type"] == "FeatureCollection"
