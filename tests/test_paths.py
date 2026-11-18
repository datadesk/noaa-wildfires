"""Offline tests of the less common paths: fallbacks, empty days, bad files and the old commands."""

import datetime
import inspect
import io
import zipfile

import pytest
import shapefile
from click.testing import CliRunner

import noaa_wildfires
from noaa_wildfires import NOAADataError
from noaa_wildfires.cli import cmd

from .conftest import DATA, FakeResponse

HEADER = b"        Lon,        Lat, YearDay, Time,       Satellite,           Method, Ecosystem,        FRP\n"
GOOD_ROW = b" -99.2,  51.3, 2026321, 0301,       GOES-EAST,             NGFS,        35,     20.360\n"
FIRE = (DATA / "hms_fire20261117.txt").read_bytes()
SMOKE = (DATA / "hms_smoke20261117.zip").read_bytes()


def getter(replies: dict[str, bytes | int]):
    """Make a request function that answers by the date at the end of the address."""

    def get(url: str, *, timeout: float) -> FakeResponse:
        for key, value in replies.items():
            if key in url:
                if isinstance(value, int):
                    return FakeResponse(status_code=value)
                return FakeResponse(value)
        return FakeResponse(status_code=404)

    return get


def zipped(**pieces: bytes) -> bytes:
    """Make a zip file from named pieces."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in pieces.items():
            zf.writestr(name.replace("_", "."), content)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def pretend_today(monkeypatch):
    """Pretend it is 2026-11-18."""
    monkeypatch.setattr(noaa_wildfires, "_today", lambda: datetime.date(2026, 11, 18))


def test_fallback_skips_a_header_only_file():
    """Today's file has only a header, so the day before is used."""
    get = getter({"20261118": HEADER, "20261117": FIRE})
    assert len(noaa_wildfires.get_hms_fires(get=get)["features"]) == 7


def test_fallback_skips_a_missing_day():
    """A missing file is skipped just like an empty one."""
    get = getter({"20261116": HEADER + GOOD_ROW})
    data = noaa_wildfires.get_hms_fires(get=get)
    assert len(data["features"]) == 1


def test_fallback_gives_up_after_three_days_back():
    """Four days with nothing in them is an error that says so."""
    get = getter({"20261114": FIRE})
    with pytest.raises(NOAADataError, match="no fire detections for 2026-11-18"):
        noaa_wildfires.get_hms_fires(get=get)


def test_smoke_fallback_gives_up():
    """The same goes for smoke."""
    with pytest.raises(NOAADataError, match="no smoke detections"):
        noaa_wildfires.get_hms_smoke(get=getter({}))


def test_explicit_empty_day_is_empty():
    """A day you asked for by date is never replaced by another."""
    get = getter({"20261118": HEADER, "20261117": FIRE})
    assert noaa_wildfires.get_hms_fires("2026-11-18", get=get)["features"] == []


def test_for_day_functions_return_none_when_missing():
    """The one-day functions say None when NOAA has no file."""
    day = datetime.date(2026, 11, 1)
    assert noaa_wildfires.get_hms_fires_for_day(day, get=getter({})) is None
    assert noaa_wildfires.get_hms_smoke_for_day(day, get=getter({})) is None


def test_for_day_functions_read_a_file():
    """The one-day functions read the file for exactly that day."""
    day = datetime.date(2026, 11, 17)
    fires = noaa_wildfires.get_hms_fires_for_day(day, get=getter({"20261117": FIRE}))
    smoke = noaa_wildfires.get_hms_smoke_for_day(day, get=getter({"20261117": SMOKE}))
    assert fires is not None
    assert smoke is not None
    assert len(fires["features"]) == 7
    assert len(smoke["features"]) == 3


def test_blank_cells_and_short_rows_are_tidied():
    """A short row gets empty text, and spaces around values are removed."""
    short = HEADER + b" -99.2,  51.3, 2026321, 0301\n"
    data = noaa_wildfires.get_hms_fires("2026-11-17", get=getter({"20261117": short}))
    assert data["features"][0]["properties"]["Method"] == ""


def test_fire_file_not_utf8():
    """Bytes that are not text are a data error."""
    with pytest.raises(NOAADataError, match="does not look like a fire file"):
        noaa_wildfires.get_hms_fires(
            "2026-11-17", get=getter({"20261117": b"\xff\xfe"})
        )


def test_fire_row_with_bad_number():
    """A latitude that is not a number is a data error."""
    bad = HEADER + b" -99.2,  north, 2026321, 0301, GOES-EAST, NGFS, 35, 20.0\n"
    with pytest.raises(NOAADataError, match="fire file"):
        noaa_wildfires.get_hms_fires("2026-11-17", get=getter({"20261117": bad}))


def test_fire_records_with_unreadable_time():
    """A row that parses as GeoJSON but not as a record raises NOAADataError."""
    bad = HEADER + b" -99.2,  51.3, 26321, 0301, GOES-EAST, NGFS, 35, 20.0\n"
    with pytest.raises(NOAADataError, match="Cannot read the NOAA time"):
        noaa_wildfires.get_hms_fire_records("2026-11-17", get=getter({"20261117": bad}))


def test_smoke_records_with_unreadable_row(monkeypatch):
    """A smoke feature without NOAA's columns raises NOAADataError."""
    broken = {"features": [{"geometry": {}, "properties": {"properties": {}}}]}
    monkeypatch.setattr(noaa_wildfires, "get_hms_smoke", lambda *a, **k: broken)
    with pytest.raises(NOAADataError, match="no 'Satellite' column"):
        noaa_wildfires.get_hms_smoke_records()


@pytest.mark.parametrize(
    "content",
    [
        b"not a zip",
        zipped(readme_txt=b"hello"),
        zipped(a_shp=b"x", a_dbf=b"x"),
        zipped(a_shp=b"x", a_shx=b"x", a_dbf=b"x"),
    ],
    ids=["not-zip", "no-shapefile", "missing-piece", "garbage-pieces"],
)
def test_bad_smoke_zip(content):
    """Anything that is not a readable zipped shapefile is a data error."""
    with pytest.raises(NOAADataError, match="not a zipped shapefile"):
        noaa_wildfires.get_hms_smoke("2026-11-17", get=getter({"20261117": content}))


def test_shapefile_with_an_empty_shape():
    """A record with no outline gets no geometry instead of breaking."""
    pieces = {key: io.BytesIO() for key in ("shp", "shx", "dbf")}
    with shapefile.Writer(shp=pieces["shp"], shx=pieces["shx"], dbf=pieces["dbf"]) as w:
        w.field("Density", "C")
        w.null()
        w.record("Light")
    data = noaa_wildfires._read_shapefile(
        pieces["shp"].getvalue(), pieces["shx"].getvalue(), pieces["dbf"].getvalue()
    )
    assert data["features"][0]["geometry"] is None
    assert data["features"][0]["properties"]["properties"] == {"Density": "Light"}


def test_round_handles_every_kind_of_value():
    """Coordinates are rounded to six places and tuples become lists."""
    rounded = noaa_wildfires._round({"a": (1.12345678, [2.0]), "b": "text", "c": 3})
    assert rounded == {"a": [1.123457, [2.0]], "b": "text", "c": 3}


def test_old_functions_keep_their_signatures():
    """The old helper functions still take their original arguments, now with optional new ones."""
    for func in (noaa_wildfires.get_hms_fires, noaa_wildfires.get_hms_smoke):
        parameters = inspect.signature(func).parameters
        assert list(parameters)[:3] == ["date", "verbose", "timeout"]
        assert all(p.default is not p.empty for p in parameters.values())
        assert "kept for existing code" in (func.__doc__ or "")


def test_old_functions_return_new_names():
    """The old functions return GeoJSON that carries NOAA's current names."""
    get = getter({"20261117": FIRE})
    properties = noaa_wildfires.get_hms_fires("2026-11-17", get=get)["features"][0][
        "properties"
    ]
    assert {"Method", "Ecosystem", "FRP"} <= set(properties)
    assert not {"Method of Detect", "Ecosys", "Fire RadPower"} & set(properties)


def test_command_smoke_with_date(fake_noaa):
    """The smoke command takes --date and prints GeoJSON."""
    result = CliRunner().invoke(cmd, ["hms-smoke", "--date", "2026-11-17"])
    assert result.exit_code == 0
    assert fake_noaa.urls[0].endswith("hms_smoke20261117.zip")


def test_command_rejects_a_tiny_timeout():
    """A timeout under one second is refused by the command line."""
    result = CliRunner().invoke(cmd, ["hms-fires", "--timeout", "0"])
    assert result.exit_code == 2


def test_command_reports_a_missing_day(fake_noaa):
    """A day with no file is one `Error:` line and exit code 1."""
    result = CliRunner().invoke(cmd, ["hms-fires", "--date", "2026-01-01"])
    assert result.exit_code == 1
    assert result.stderr.startswith("Error: NOAA has no fire file for 2026-01-01")


def test_command_lists_both_commands():
    """The old command names are still there."""
    result = CliRunner().invoke(cmd, ["--help"])
    assert "hms-fires" in result.output
    assert "hms-smoke" in result.output
