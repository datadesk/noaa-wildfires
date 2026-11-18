import click

from noaa_wildfires import get_hms_fires, get_hms_smoke

DATE_HELP = "The day to download, like 2026-11-17. Defaults to the latest day."


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfires data from NOAA.

    Returns GeoJSON.
    """
    pass


@cmd.command(help="The latest fires from Hazard Mapping System satellites")
@click.option("--date", default=None, help=DATE_HELP)
def hms_fires(date):
    click.echo(get_hms_fires(date))


@cmd.command(help="The latest smoke data from Hazard Mapping System satellites")
@click.option("--date", default=None, help=DATE_HELP)
def hms_smoke(date):
    click.echo(get_hms_smoke(date))


if __name__ == "__main__":
    cmd()
