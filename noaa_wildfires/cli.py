"""The noaawildfires command-line interface."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click

from noaa_wildfires import NOAAError, get_hms_fires, get_hms_smoke
from noaa_wildfires.fetch import DEFAULT_TIMEOUT

DATE_HELP = "The day to download, like 2026-11-17. Defaults to the latest day."


def _common_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Add the options both download commands share.

    Args:
        func: The click command function to decorate.

    Returns:
        The same function with the date, timeout and verbose options attached.
    """
    decorators = [
        click.option("--date", default=None, help=DATE_HELP),
        click.option(
            "--timeout",
            default=DEFAULT_TIMEOUT,
            show_default=True,
            type=click.FloatRange(min=1),
            help="Seconds to wait for NOAA on each try",
        ),
        click.option("--verbose", is_flag=True, help="Print each request to stderr"),
    ]
    for decorator in reversed(decorators):
        func = decorator(func)
    return func


@click.group()
def cmd() -> None:
    """
    A command-line interface for downloading wildfires data from NOAA.

    Returns GeoJSON.
    """
    pass


@cmd.command(help="The latest fires from Hazard Mapping System satellites")
@_common_options
def hms_fires(date, timeout, verbose):
    try:
        data = get_hms_fires(date, verbose, timeout)
    except (NOAAError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(data)


@cmd.command(help="The latest smoke data from Hazard Mapping System satellites")
@_common_options
def hms_smoke(date, timeout, verbose):
    try:
        data = get_hms_smoke(date, verbose, timeout)
    except (NOAAError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(data)


if __name__ == "__main__":
    cmd()
