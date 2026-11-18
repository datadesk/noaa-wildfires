"""Typed records for the fires and smoke NOAA publishes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

NO_POWER_VALUE = -999.0
"""What NOAA writes in the FRP column when it has no measurement."""


def parse_noaa_time(day: str, clock: str) -> datetime:
    """Read the date and time NOAA writes in its files.

    NOAA writes the day as the year followed by the day of the year, such as
    "2026321" for the 321st day of 2026, and the time as hours and minutes,
    such as "0617". Both are in UTC.

    Args:
        day: The year and day of the year, as seven digits.
        clock: The hours and minutes, as four digits.

    Returns:
        A time that carries its time zone, UTC.

    Raises:
        ValueError: If either value is not written the way NOAA writes it.

    Examples:
        >>> parse_noaa_time("2026321", "0617").isoformat()
        '2026-11-17T06:17:00+00:00'
    """
    if len(day) != 7 or not day.isdigit() or len(clock) != 4 or not clock.isdigit():
        raise ValueError(f"Cannot read the NOAA time {day!r} {clock!r}")
    start = datetime(int(day[:4]), 1, 1, tzinfo=UTC)
    return start + timedelta(
        days=int(day[4:]) - 1, hours=int(clock[:2]), minutes=int(clock[2:])
    )


@dataclass(frozen=True, slots=True)
class HmsFire:
    """One fire detection from the Hazard Mapping System.

    A detection is a spot that looked hot to a satellite, or that an analyst
    added after looking at satellite images. It is not a confirmed wildfire.

    Attributes:
        latitude: Degrees north of the equator, negative in the south.
        longitude: Degrees east of the prime meridian, negative in the west.
        observed_at: When the satellite saw the spot, in UTC.
        satellite: The satellite that saw it, as NOAA writes it, such as
            "NOAA 20", "NOAA 21", "GOES-EAST" or "GOES-WEST".
        method: How the spot was found, as NOAA writes it, such as "VIIRS",
            "NGFS" or "ANALYSIS".
        ecosystem: NOAA's number for the kind of land the spot is on.
        frp: Fire radiative power in megawatts, a measure of the heat the
            fire gives off. None when NOAA has no measurement, which it marks
            with -999.

    Examples:
        >>> fire = HmsFire.from_properties(
        ...     {
        ...         "Lon": "-81.140587",
        ...         "Lat": "42.939484",
        ...         "YearDay": "2026321",
        ...         "Time": "0617",
        ...         "Satellite": "NOAA 20",
        ...         "Method": "VIIRS",
        ...         "Ecosystem": "55",
        ...         "FRP": "1.620",
        ...     }
        ... )
        >>> fire.observed_at.isoformat()
        '2026-11-17T06:17:00+00:00'
        >>> fire.frp
        1.62
    """

    latitude: float
    longitude: float
    observed_at: datetime
    satellite: str
    method: str
    ecosystem: int
    frp: float | None

    @classmethod
    def from_properties(cls, properties: dict[str, str]) -> HmsFire:
        """Make a record from the properties that ``get_hms_fires`` returns.

        Args:
            properties: The properties of one feature from ``get_hms_fires``.

        Returns:
            The record.

        Raises:
            ValueError: If a column is missing or a value cannot be read.

        Examples:
            >>> HmsFire.from_properties({"Lon": "1", "Lat": "2"})
            Traceback (most recent call last):
                ...
            ValueError: NOAA's fire row has no 'FRP' column
        """
        try:
            frp = float(properties["FRP"])
            return cls(
                latitude=float(properties["Lat"]),
                longitude=float(properties["Lon"]),
                observed_at=parse_noaa_time(properties["YearDay"], properties["Time"]),
                satellite=properties["Satellite"],
                method=properties["Method"],
                ecosystem=int(properties["Ecosystem"]),
                frp=None if frp == NO_POWER_VALUE else frp,
            )
        except KeyError as error:
            raise ValueError(f"NOAA's fire row has no {error} column") from error


@dataclass(frozen=True, slots=True)
class HmsSmoke:
    """One smoke area from the Hazard Mapping System.

    Analysts draw these outlines by looking at satellite images. An outline is
    where smoke could be seen from space. It says nothing about the smoke near
    the ground.

    Attributes:
        geometry: The outline, as a GeoJSON polygon in longitude and latitude.
        satellite: The satellite whose images were used, as NOAA writes it.
        start: When the smoke was first seen in the images used, in UTC.
        end: When the smoke was last seen in the images used, in UTC.
        density: How thick the smoke looks from above: "Light", "Medium" or
            "Heavy".

    Examples:
        >>> smoke = HmsSmoke.from_feature(
        ...     {
        ...         "geometry": {"type": "Polygon", "coordinates": []},
        ...         "properties": {
        ...             "properties": {
        ...                 "Satellite": "GOES-WEST",
        ...                 "Start": "2026321 1300",
        ...                 "End": "2026321 1600",
        ...                 "Density": "Light",
        ...             }
        ...         },
        ...     }
        ... )
        >>> smoke.start.isoformat()
        '2026-11-17T13:00:00+00:00'
        >>> smoke.density
        'Light'
    """

    geometry: dict[str, Any]
    satellite: str
    start: datetime
    end: datetime
    density: str

    @classmethod
    def from_feature(cls, feature: dict[str, Any]) -> HmsSmoke:
        """Make a record from a feature that ``get_hms_smoke`` returns.

        Args:
            feature: One feature from ``get_hms_smoke``.

        Returns:
            The record.

        Raises:
            ValueError: If a column is missing or a value cannot be read.

        Examples:
            >>> HmsSmoke.from_feature({"geometry": None, "properties": {}})
            Traceback (most recent call last):
                ...
            ValueError: NOAA's smoke row has no 'properties' column
        """
        try:
            attributes = feature["properties"]["properties"]
            return cls(
                geometry=dict(feature["geometry"]),
                satellite=attributes["Satellite"],
                start=_parse_smoke_time(attributes["Start"]),
                end=_parse_smoke_time(attributes["End"]),
                density=attributes["Density"],
            )
        except KeyError as error:
            raise ValueError(f"NOAA's smoke row has no {error} column") from error


def _parse_smoke_time(text: str) -> datetime:
    """Read a smoke time, which NOAA writes like "2026321 1300".

    Args:
        text: The year and day of the year, a space and the hours and minutes.

    Returns:
        A time that carries its time zone, UTC.

    Raises:
        ValueError: If the text is not written the way NOAA writes it.

    Examples:
        >>> _parse_smoke_time("2026321 1300").isoformat()
        '2026-11-17T13:00:00+00:00'
    """
    day, _, clock = text.partition(" ")
    return parse_noaa_time(day, clock)
