# noaa-wildfires

Download wildfires data from NOAA satellites

```{contents} Table of contents
:local:
:depth: 2
```

## Installation

```sh
uv add noaa-wildfires
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
uv sync --all-groups
```

Run the offline tests, the linter and the type checker.

```sh
make check
```

The tests that call NOAA's real website are skipped by default. Run them with `make test-live`.

## Developing the CLI

The command-line interface is implemented using Click. `uv sync` installs the package in editable form, so the `noaawildfires` command is ready to use with `uv run`.

```sh
uv run noaawildfires --help
```

## Other resources

* Issues: [github.com/datadesk/noaa-wildfires/issues](https://github.com/datadesk/noaa-wildfires/issues)
* Packaging: [pypi.python.org/pypi/noaa-wildfires](https://pypi.python.org/pypi/noaa-wildfires)
* Testing: [github.com/datadesk/noaa-wildfires/actions](https://github.com/datadesk/noaa-wildfires/actions)
