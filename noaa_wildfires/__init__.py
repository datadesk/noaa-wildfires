"""Methods for downloading wildfires data from NOAA's Hazard Mapping System."""

from __future__ import annotations

import csv
import datetime
import io
import struct
import zipfile
from typing import Any

import requests
import shapefile
from geojson import Feature, FeatureCollection, Point

__all__ = [
    "fire_url",
    "get_hms_fires",
    "get_hms_fires_for_day",
    "get_hms_smoke",
    "get_hms_smoke_for_day",
    "smoke_url",
]

BASE_URL = "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS"
"""Where NOAA publishes one fire file and one smoke file for every day."""

DAYS_TO_LOOK_BACK = 3
"""How many days before today to try when today's file is missing or empty."""


def get_hms_fires(date: datetime.date | str | None = None) -> FeatureCollection:
    """Get fires from the Hazard Mapping System satellites.

    NOAA publishes one file of fire detections for each day, in UTC. With no
    date, this reads today's file, which grows through the day. If today's file
    does not exist yet or has no detections yet, it falls back to the most
    recent day that has some, looking back up to three days.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with detections.

    Returns:
        A GeoJSON feature collection with one point for each fire. The
        properties are the columns of NOAA's file, as text, with NOAA's
        current names: Lon, Lat, YearDay, Time, Satellite, Method, Ecosystem
        and FRP.

    Note:
        This function is kept for existing code. It now reads NOAA's current
        daily files instead of ones NOAA stopped updating in 2022, and its
        properties use NOAA's current column names. ``Method of Detect`` is now
        ``Method``, ``Ecosys`` is ``Ecosystem`` and ``Fire RadPower`` is ``FRP``.

    Raises:
        ValueError: If NOAA has no file for the day you asked for, or for any of
            the recent days when you did not ask for one.

    Examples:
        >>> import noaa_wildfires
        >>> data = noaa_wildfires.get_hms_fires()
        >>> data = noaa_wildfires.get_hms_fires("2026-11-17")
    """
    return _get_latest("fire", get_hms_fires_for_day, date)


def get_hms_smoke(date: datetime.date | str | None = None) -> FeatureCollection:
    """Get smoke from the Hazard Mapping System satellites.

    NOAA publishes one file of smoke polygons for each day, in UTC. With no
    date, this reads today's file. If today's file does not exist yet or has no
    smoke yet, it falls back to the most recent day that has some, looking back
    up to three days.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with smoke.

    Returns:
        A GeoJSON feature collection with one polygon for each smoke area.

    Note:
        This function is kept for existing code. It now reads NOAA's current
        daily files instead of ones NOAA stopped updating in 2022. NOAA's
        smoke ``Density`` is now the word Light, Medium or Heavy, not a number.

    Raises:
        ValueError: If NOAA has no file for the day you asked for, or for any of
            the recent days when you did not ask for one.

    Examples:
        >>> import noaa_wildfires
        >>> data = noaa_wildfires.get_hms_smoke()
        >>> data = noaa_wildfires.get_hms_smoke("2026-11-17")
    """
    return _get_latest("smoke", get_hms_smoke_for_day, date)


def get_hms_fires_for_day(day: datetime.date) -> FeatureCollection | None:
    """Download the fire file for one day.

    Args:
        day: The day to download.

    Returns:
        A GeoJSON feature collection, or None if NOAA has no file for that day.

    Examples:
        >>> data = get_hms_fires_for_day(datetime.date(2026, 11, 17))
    """
    content = _download(fire_url(day))
    if content is None:
        return None
    lines = content.decode("utf-8").splitlines()
    reader = csv.DictReader(lines, delimiter=",")

    # Tidy it up, keeping NOAA's column names
    tidy_reader = []
    for row in reader:
        tidy_row = {k.strip(): (v or "").strip() for k, v in row.items()}
        tidy_reader.append(tidy_row)

    # Convert it to GeoJSON
    features = [
        Feature(geometry=Point(map(float, [r["Lon"], r["Lat"]])), properties=r)
        for r in tidy_reader
    ]
    return FeatureCollection(features)


def get_hms_smoke_for_day(day: datetime.date) -> FeatureCollection | None:
    """Download the smoke file for one day.

    Args:
        day: The day to download.

    Returns:
        A GeoJSON feature collection, or None if NOAA has no file for that day.

    Examples:
        >>> data = get_hms_smoke_for_day(datetime.date(2026, 11, 17))
    """
    content = _download(smoke_url(day))
    if content is None:
        return None
    return _parse_shapefile_zip(content)


def fire_url(day: datetime.date) -> str:
    """Make the address of the fire file for one day.

    Args:
        day: The day.

    Returns:
        The address.

    Examples:
        >>> fire_url(datetime.date(2026, 11, 17))
        'https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Fire_Points/Text/2026/11/hms_fire20261117.txt'
    """
    return f"{BASE_URL}/Fire_Points/Text/{day:%Y/%m}/hms_fire{day:%Y%m%d}.txt"


def smoke_url(day: datetime.date) -> str:
    """Make the address of the smoke file for one day.

    Args:
        day: The day.

    Returns:
        The address.

    Examples:
        >>> smoke_url(datetime.date(2026, 11, 17))
        'https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Smoke_Polygons/Shapefile/2026/11/hms_smoke20261117.zip'
    """
    return f"{BASE_URL}/Smoke_Polygons/Shapefile/{day:%Y/%m}/hms_smoke{day:%Y%m%d}.zip"


def _today() -> datetime.date:
    """Get today's date in UTC, which is the time NOAA's files use.

    Returns:
        Today's date.

    Examples:
        >>> _today() > datetime.date(2026, 1, 1)
        True
    """
    return datetime.datetime.now(datetime.UTC).date()


def _get_latest(kind, reader, date) -> FeatureCollection:
    """Read one day's file, or find the latest day that has something in it.

    Args:
        kind: The word "fire" or "smoke", used in error messages.
        reader: The function that downloads one day.
        date: The day asked for, or None for the latest.

    Returns:
        A GeoJSON feature collection.

    Raises:
        ValueError: If there is nothing to return.

    Examples:
        >>> data = _get_latest("fire", get_hms_fires_for_day, None)
    """
    if date is not None:
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        data = reader(date)
        if data is None:
            raise ValueError(f"NOAA has no {kind} file for {date}")
        return data

    today = _today()
    for days_back in range(DAYS_TO_LOOK_BACK + 1):
        data = reader(today - datetime.timedelta(days=days_back))
        if data is not None and data["features"]:
            return data
    raise ValueError(
        f"NOAA has no {kind} detections for {today} or the {DAYS_TO_LOOK_BACK} days before it"
    )


def _download(url: str) -> bytes | None:
    """Download a file.

    Args:
        url: The address.

    Returns:
        The bytes of the file, or None if NOAA says there is no such file.

    Raises:
        requests.HTTPError: If NOAA answers with any other error.

    Examples:
        >>> content = _download(fire_url(datetime.date(2026, 11, 17)))
    """
    r = requests.get(url)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return bytes(r.content)


def _parse_shapefile_zip(content: bytes) -> FeatureCollection:
    """Read a zipped shapefile and convert it to GeoJSON.

    Args:
        content: The bytes of the zip file.

    Returns:
        A GeoJSON feature collection, with one feature for each shape.

    Raises:
        ValueError: If the bytes are not a zip file with a readable shapefile in
            it.

    Examples:
        >>> data = _parse_shapefile_zip(open("hms_smoke20261117.zip", "rb").read())
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = {name.lower(): name for name in zf.namelist()}
            stem = next(n for n in names if n.endswith(".shp"))[:-4]
            pieces = {
                ext: zf.read(names[f"{stem}.{ext}"]) for ext in ("shp", "shx", "dbf")
            }
        return _read_shapefile(pieces["shp"], pieces["shx"], pieces["dbf"])
    except (
        zipfile.BadZipFile,
        StopIteration,
        KeyError,
        struct.error,
        shapefile.ShapefileException,
    ) as error:
        raise ValueError(f"not a zipped shapefile: {error!r}") from error


def _read_shapefile(shp: bytes, shx: bytes, dbf: bytes) -> FeatureCollection:
    """Convert the bytes of a shapefile's three main pieces to GeoJSON.

    Each feature keeps the odd shape it has always had: its properties hold a
    copy of the whole feature, with the attributes inside under "properties".

    Args:
        shp: The bytes of the .shp file, which holds the shapes.
        shx: The bytes of the .shx file, which indexes the shapes.
        dbf: The bytes of the .dbf file, which holds the attributes.

    Returns:
        A GeoJSON feature collection, with one feature for each shape.

    Examples:
        >>> data = _read_shapefile(shp_bytes, shx_bytes, dbf_bytes)
    """
    reader = shapefile.Reader(
        shp=io.BytesIO(shp), shx=io.BytesIO(shx), dbf=io.BytesIO(dbf)
    )
    features = []
    for i, (shape, record) in enumerate(
        zip(reader.shapes(), reader.records(), strict=True)
    ):
        geometry = None if shape is None else _round(shape.__geo_interface__)
        whole = {
            "type": "Feature",
            "id": str(i),
            "geometry": geometry,
            "properties": {} if record is None else record.as_dict(),
        }
        features.append(Feature(geometry=geometry, properties=whole))
    return FeatureCollection(features)


def _round(value: Any) -> Any:
    """Round every coordinate to the six decimal places NOAA publishes.

    Args:
        value: A GeoJSON geometry, or any list, tuple or number inside one.

    Returns:
        The same value with every float rounded and every tuple turned into a
        list.

    Examples:
        >>> _round({"type": "Point", "coordinates": (1.12345678, 2.0)})
        {'type': 'Point', 'coordinates': [1.123457, 2.0]}
    """
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_round(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    return value
