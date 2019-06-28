noaa_wildfires
==============

Download wildfires data from NOAA satellites

Installation
------------

::

    $ pipenv install noaa_wildfires


Command-line usage
------------------

::

    Usage: noaawildfires [OPTIONS] COMMAND [ARGS]...

      A command-line interface for downloading smoke and wilfire data from NOAA.

      Returns GeoJSON.

    Options:
      --help  Show this message and exit.

    Commands:
      hms-fires  The latest fires from Hazard Mapping System satellites
      hms-smoke  The latest smoke data from Hazard Mapping System satellites


Download the latest fires from Hazard Mapping System satellites. ::

    $ noaawildfires hms-fires


Download the latest smoke data from Hazard Mapping System satellites. ::

    $ noaawildfires hms-smoke


Python usage
------------

Import the library. ::

    >>> import noaa_wildfires

Download the latest fires from Hazard Mapping System satellites ::

    >>> data = noaa_wildfires.get_hms_fires()

Download the latest smoke data from Hazard Mapping System satellites ::

    >>> data = noaa_wildfires.get_hms_smoke()


Contributing
------------

Install dependencies for development ::

    $ pipenv install --dev

Run tests ::

    $ make test

Ship new version to PyPI ::

    $ make ship


Developing the CLI
------------------

The command-line interface is implemented using Click and setuptools. To install it locally for development inside your virtual environment, run the following installation command, as `prescribed by the Click documentation <https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration>`_. ::

    $ pip install --editable .
