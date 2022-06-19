```{include} _templates/nav.html
```

# noaa-wildfires

Download wildfires data from NOAA satellites

```{contents} Table of contents
:local:
:depth: 2
```

## Installation

```sh
pipenv install noaa-wildfires
```

## Command-line usage

```sh
Usage: noaawildfires [OPTIONS] COMMAND [ARGS]...

  A command-line interface for downloading wildfires data from NOAA.

  Returns GeoJSON.

Options:
  --help  Show this message and exit.

Commands:
  hms-fires  The latest fires from Hazard Mapping System satellites
  hms-smoke  The latest smoke data from Hazard Mapping System satellites
```

Download the latest fires from Hazard Mapping System satellites.

```sh
noaawildfires hms-fires
```

Download the latest smoke data from Hazard Mapping System satellites.

```sh
noaawildfires hms-smoke
```

## Python usage

Import the library.

```python
import noaa_wildfires
```

Download the latest fires from Hazard Mapping System satellites.

```python
noaa_wildfires.get_hms_fires()
```

Download the latest smoke data from Hazard Mapping System satellites.

```python
noaa_wildfires.get_hms_smoke()
```

## Contributing

Install dependencies for development.

```sh
pipenv install --dev
```

Run tests.

```sh
pipenv run python test.py
```

## Developing the CLI

The command-line interface is implemented using Click and setuptools. To install it locally for development inside your virtual environment, run the following installation command, as [prescribed by the Click documentation](https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration).

```sh
pipenv run pip install --editable .
```

## Links

* Docs: [palewi.re/docs/noaa-wildfires/](https://palewi.re/docs/noaa-wildfires/)
* Issues: [github.com/datadesk/noaa-wildfires/issues](https://github.com/datadesk/noaa-wildfires/issues)
* Packaging: [pypi.python.org/pypi/noaa-wildfires](https://pypi.python.org/pypi/noaa-wildfires)
* Testing: [github.com/datadesk/noaa-wildfires/actions](https://github.com/datadesk/noaa-wildfires/actions)
