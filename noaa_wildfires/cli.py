import click
from noaa_wildfires import get_hms_fires, get_hms_smoke


@click.group()
def cmd():
    """
    A command-line interface for downloading smoke and wilfire data from NOAA.

    Returns GeoJSON.
    """
    pass


@cmd.command(help="The latest fires from Hazard Mapping System satellites")
def hms_fires():
    click.echo(get_hms_fires())


@cmd.command(help="The latest smoke data from Hazard Mapping System satellites")
def hms_smoke():
    click.echo(get_hms_smoke())


if __name__ == '__main__':
    cmd()
