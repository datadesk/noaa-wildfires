"""Methods for downloading wildfires data from NOAA's Hazard Mapping System."""

from __future__ import annotations

import csv
import datetime
import io
import struct
import zipfile
from collections.abc import Callable
from typing import Any

import shapefile
from geojson import Feature, FeatureCollection, Point

from .errors import NOAADataError, NOAAError
from .fetch import DEFAULT_TIMEOUT, download
from .records import HmsFire, HmsSmoke

__all__ = [
    "DEFAULT_TIMEOUT",
    "HmsFire",
    "HmsSmoke",
    "NOAADataError",
    "NOAAError",
    "fire_url",
    "get_hms_fire_records",
    "get_hms_fires",
    "get_hms_fires_for_day",
    "get_hms_smoke",
    "get_hms_smoke_for_day",
    "get_hms_smoke_records",
    "smoke_url",
]

BASE_URL = "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS"
"""Where NOAA publishes one fire file and one smoke file for every day."""

DAYS_TO_LOOK_BACK = 3
"""How many days before today to try when today's file is missing or empty."""


def get_hms_fires(
    date: datetime.date | str | None = None,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> FeatureCollection:
    """Get fires from the Hazard Mapping System satellites.

    NOAA publishes one file of fire detections for each day, in UTC. With no
    date, this reads today's file, which grows through the day. If today's file
    does not exist yet or has no detections yet, it falls back to the most
    recent day that has some, looking back up to three days.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with detections.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

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
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If NOAA has no file for the day you asked for, or for
            any of the recent days when you did not ask for one, or if the
            file cannot be read. This is also a ``ValueError``.

    Examples:
        >>> import noaa_wildfires
        >>> data = noaa_wildfires.get_hms_fires()
        >>> data = noaa_wildfires.get_hms_fires("2026-11-17", timeout=30)
    """
    return _get_latest("fire", get_hms_fires_for_day, date, verbose, timeout)


def get_hms_smoke(
    date: datetime.date | str | None = None,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> FeatureCollection:
    """Get smoke from the Hazard Mapping System satellites.

    NOAA publishes one file of smoke polygons for each day, in UTC. With no
    date, this reads today's file. If today's file does not exist yet or has no
    smoke yet, it falls back to the most recent day that has some, looking back
    up to three days.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with smoke.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

    Returns:
        A GeoJSON feature collection with one polygon for each smoke area.

    Note:
        This function is kept for existing code. It now reads NOAA's current
        daily files instead of ones NOAA stopped updating in 2022. NOAA's
        smoke ``Density`` is now the word Light, Medium or Heavy, not a number.

    Raises:
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If NOAA has no file for the day you asked for, or for
            any of the recent days when you did not ask for one, or if the
            file cannot be read. This is also a ``ValueError``.

    Examples:
        >>> import noaa_wildfires
        >>> data = noaa_wildfires.get_hms_smoke()
        >>> data = noaa_wildfires.get_hms_smoke("2026-11-17", timeout=30)
    """
    return _get_latest("smoke", get_hms_smoke_for_day, date, verbose, timeout)


def get_hms_fire_records(
    date: datetime.date | str | None = None,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[HmsFire]:
    """Get fires from the Hazard Mapping System satellites, as typed records.

    This reads the same file as ``get_hms_fires``, with the numbers already
    parsed and one timezone-aware UTC ``observed_at`` time. See ``HmsFire`` for
    every field.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with detections.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

    Returns:
        A list of ``HmsFire`` records, one for each detection.

    Raises:
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If NOAA has no file for the day, or a row cannot be
            read. This is also a ``ValueError``.

    Examples:
        >>> import noaa_wildfires
        >>> for fire in noaa_wildfires.get_hms_fire_records():
        ...     print(fire.observed_at, fire.latitude, fire.longitude, fire.frp)
    """
    data = get_hms_fires(date, verbose, timeout)
    try:
        return [HmsFire.from_properties(f["properties"]) for f in data["features"]]
    except ValueError as error:
        raise NOAADataError(str(error)) from error


def get_hms_smoke_records(
    date: datetime.date | str | None = None,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[HmsSmoke]:
    """Get smoke from the Hazard Mapping System satellites, as typed records.

    This reads the same file as ``get_hms_smoke``, with the times parsed into
    timezone-aware UTC datetimes. See ``HmsSmoke`` for every field.

    Args:
        date: The day to download, as a ``datetime.date`` or text like
            "2026-11-17". Defaults to the latest day with smoke.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

    Returns:
        A list of ``HmsSmoke`` records, one for each smoke area.

    Raises:
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If NOAA has no file for the day, or a row cannot be
            read. This is also a ``ValueError``.

    Examples:
        >>> import noaa_wildfires
        >>> for smoke in noaa_wildfires.get_hms_smoke_records():
        ...     print(smoke.density, smoke.start, smoke.end)
    """
    data = get_hms_smoke(date, verbose, timeout)
    try:
        return [HmsSmoke.from_feature(f) for f in data["features"]]
    except ValueError as error:
        raise NOAADataError(str(error)) from error


def get_hms_fires_for_day(
    day: datetime.date,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> FeatureCollection | None:
    """Download the fire file for one day.

    Args:
        day: The day to download.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

    Returns:
        A GeoJSON feature collection, or None if NOAA has no file for that day.

    Raises:
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If the file cannot be read.

    Examples:
        >>> data = get_hms_fires_for_day(datetime.date(2026, 11, 17))
    """
    url = fire_url(day)
    content = download(url, verbose, timeout)
    if content is None:
        return None
    try:
        lines = content.decode("utf-8").splitlines()
        reader = csv.DictReader(lines, delimiter=",")
        columns = [name.strip() for name in reader.fieldnames or []]
        if "Lon" not in columns or "Lat" not in columns:
            raise ValueError("it has no Lon and Lat columns")

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
    except (UnicodeDecodeError, KeyError, ValueError, AttributeError) as error:
        raise NOAADataError(
            f"The file at {url} does not look like a fire file: {error}", url=url
        ) from error
    return FeatureCollection(features)


def get_hms_smoke_for_day(
    day: datetime.date,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> FeatureCollection | None:
    """Download the smoke file for one day.

    Args:
        day: The day to download.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.

    Returns:
        A GeoJSON feature collection, or None if NOAA has no file for that day.

    Raises:
        NOAAError: If NOAA cannot be reached after several tries, or answers
            with an error.
        NOAADataError: If the file cannot be read.

    Examples:
        >>> data = get_hms_smoke_for_day(datetime.date(2026, 11, 17))
    """
    url = smoke_url(day)
    content = download(url, verbose, timeout)
    if content is None:
        return None
    try:
        return _parse_shapefile_zip(content)
    except ValueError as error:
        raise NOAADataError(
            f"The file at {url} is not a zipped shapefile: {error}", url=url
        ) from error


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


def _get_latest(
    kind: str,
    reader: Callable[[datetime.date, bool, float], FeatureCollection | None],
    date: datetime.date | str | None,
    verbose: bool,
    timeout: float,
) -> FeatureCollection:
    """Read one day's file, or find the latest day that has something in it.

    Args:
        kind: The word "fire" or "smoke", used in error messages.
        reader: The function that downloads one day.
        date: The day asked for, or None for the latest.
        verbose: Print each request to standard error.
        timeout: Seconds to wait for NOAA on each try.

    Returns:
        A GeoJSON feature collection.

    Raises:
        NOAADataError: If there is nothing to return.

    Examples:
        >>> data = _get_latest("fire", get_hms_fires_for_day, None, False, 60.0)
    """
    if date is not None:
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        data = reader(date, verbose, timeout)
        if data is None:
            raise NOAADataError(f"NOAA has no {kind} file for {date}")
        return data

    today = _today()
    for days_back in range(DAYS_TO_LOOK_BACK + 1):
        day = today - datetime.timedelta(days=days_back)
        data = reader(day, verbose, timeout)
        if data is not None and data["features"]:
            return data
    raise NOAADataError(
        f"NOAA has no {kind} detections for {today} or the {DAYS_TO_LOOK_BACK} days before it"
    )


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
