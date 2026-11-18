# noaa-wildfires

Download wildfire detections and smoke outlines from NOAA's [Hazard Mapping System (HMS)](https://www.ospo.noaa.gov/products/land/hms.html)

```{contents} Table of contents
:local:
:depth: 2
```

## Read this first

**A fire detection is a hot spot seen by a satellite. It is not a confirmed wildfire. A smoke outline is where an analyst saw smoke from space. It is not a measure of the air you breathe.**

NOAA's Hazard Mapping System starts with fire detections that computer programs make from satellite images, and adds smoke outlines that analysts draw by looking at satellite images. This is what NOAA says about the fire points:

* A point is "the center latitude/longitude coordinates of the corresponding satellite pixel in which a potential fire event was detected." The fire itself can be anywhere inside the pixel, and offsets can run from tens or hundreds of meters (VIIRS) to about a kilometer (GOES). Steep terrain can make the error larger.
* "Fire pixels do not translate into absolute fire area and their use should serve as a coarse indicator only."
* "Some industrial heat sources (e.g., gas flares, steel mills) and highly reflective surfaces (e.g., solar panels) may generate signals similar to those from fires, though most of these are filtered out during data processing." False alarms can also come from fresh burn scars, sandy soil and sun glint.
* Fires can be missed: "cloud cover, dense smoke, forest canopy, terrain, and the fire's size or intensity" all change what a satellite can see.
* HMS is "forward processing", so "any data gap due to planned or unplanned system downtimes or other data flow interruptions will not be back-filled". The mix of satellites changes over time, which changes how many detections there are. Do not compare counts across years without reading NOAA's notes.

NOAA's warning, word for word: "The information on fire position should be used as general guidance and for strategic planning. Tactical decisions, such as the activation of a response to fight these fires and evacuation efforts, should not be made without other information to corroborate the fire's existence and location."

On smoke, NOAA says that smoke analysis "is conducted using daytime imagery from GOES satellites", that the first classification comes out between 11:00 AM and 12:00 PM Eastern Time and a second one between 7:00 PM and 8:00 PM, and that thick smoke can be confused with cloud. Smoke mapping "can be greatly affected by the observation conditions (most often as a result of cloud interference) which can lead to incomplete representation of smoke coverage."

```{note}
NOAA's HMS page also carries this notice: "Due to recent advancements in NOAA's satellite-based fire monitoring products, the Satellite Analysis Branch intends to transition away from routine manual verification of automated fire detections within the Hazard Mapping System." Fire points may therefore become less checked by people over time. The page links to a longer explanation that this package's author did not read.
```

## Installation

```bash
uv add noaa-wildfires
```

## Quick start

From the shell, print GeoJSON for the latest day of fires.

```bash
noaawildfires hms-fires > fires.json
```

From Python, ask for typed records and read their fields.

```python
import noaa_wildfires

for fire in noaa_wildfires.get_hms_fire_records("2026-11-17"):
    print(fire.observed_at, fire.latitude, fire.longitude, fire.frp)
```

## Which day you get

NOAA publishes one file of fires and one file of smoke for each day, with days counted in UTC. The file for today grows as new satellite images arrive. NOAA says first detections are "typically published online by 8:00 AM Eastern Time", and that polar-orbiting satellite data arrives a few hours late, so a detection can show up long after the satellite saw it.

With no date, this package reads today's file. If today's file is missing or has no rows yet, it tries yesterday, then the day before, up to three days back, and uses the first day that has something. Pass a date to get exactly that day instead. A day with no file raises an error. Smoke files for a day are often empty early in the day, before the first analysis.

## Command-line usage

```bash
Usage: noaawildfires [OPTIONS] COMMAND [ARGS]...

  A command-line interface for downloading wildfires data from NOAA.

  Returns GeoJSON.

Options:
  --help  Show this message and exit.

Commands:
  hms-fires  The latest fires from Hazard Mapping System satellites
  hms-smoke  The latest smoke data from Hazard Mapping System satellites
```

Both commands print GeoJSON and take the same options.

| Option | What it does |
| --- | --- |
| `--date TEXT` | The day to download, like `2026-11-17`. The default is the latest day with data. |
| `--timeout FLOAT` | Seconds to wait for NOAA on each try. The default is 60. |
| `--verbose` | Print each request to standard error. The JSON on standard output is not touched. |

Examples:

```bash
# The latest fires
noaawildfires hms-fires > fires.json

# The smoke outlines for one day
noaawildfires hms-smoke --date 2026-11-17 > smoke.json

# Show each request, and wait up to two minutes for NOAA
noaawildfires hms-fires --verbose --timeout 120 > fires.json
```

A failure prints one line starting with `Error:` and exits with code 1.

## Python usage

Import the package.

```python
import noaa_wildfires
```

### GeoJSON

`get_hms_fires` returns a GeoJSON feature collection with one point for each detection. The properties are NOAA's columns, as text, with NOAA's current names. This function is kept for existing code, and what it returns changed: see [What changed in this release](#what-changed-in-this-release).

```python
data = noaa_wildfires.get_hms_fires()
data = noaa_wildfires.get_hms_fires("2026-11-17")
```

`get_hms_smoke` returns a feature collection with one polygon for each smoke outline.

```python
data = noaa_wildfires.get_hms_smoke()
data = noaa_wildfires.get_hms_smoke("2026-11-17")
```

Each smoke feature keeps the odd shape it had in older versions: its `properties` hold a copy of the whole feature, with NOAA's columns inside it under `properties`. The typed records below are easier to read.

### Typed records

`get_hms_fire_records` and `get_hms_smoke_records` return lists of `HmsFire` and `HmsSmoke` objects. The numbers are already numbers, and times are in UTC and carry their time zone.

```python
fires = noaa_wildfires.get_hms_fire_records("2026-11-17")
first = fires[0]
first.observed_at  # datetime.datetime(2026, 11, 17, 3, 1, tzinfo=datetime.timezone.utc)
first.satellite  # "GOES-EAST"
first.frp  # 20.36

smoke = noaa_wildfires.get_hms_smoke_records("2026-11-17")
smoke[0].density  # "Light"
smoke[0].geometry["type"]  # "Polygon"
```

### Errors and retries

Each request waits at most 60 seconds for NOAA. A request that cannot reach NOAA, times out, or gets a server error (status 500 and up) or "too many requests" (429) is tried again, up to four tries in all, with a longer pause each time. Other errors fail right away.

When it still fails, the package raises `noaa_wildfires.NOAAError`, which carries the `url` and the `status_code`. If NOAA has no file for the day you asked for, or a file arrives but cannot be read, it raises `noaa_wildfires.NOAADataError`, which is also a `ValueError`.

```python
try:
    data = noaa_wildfires.get_hms_fires(timeout=30)
except noaa_wildfires.NOAAError as error:
    print(error)
```

### Use your own request function

Some projects send every web request through their own helper, for shared retries, logging or proxy settings. Pass that helper as `get` and the package will use it instead of `requests.get`. It is called like `get(url, timeout=seconds)` and must return something with a `status_code` and the file's `content` as bytes. The timeout and retries still work, and failures still raise `NOAAError`.

```python
import requests

import noaa_wildfires
from noaa_wildfires import Reply


def my_get(url: str, *, timeout: float) -> Reply:
    print("Asking for", url)
    return requests.get(url, timeout=timeout, headers={"User-Agent": "my-project"})


data = noaa_wildfires.get_hms_fires(get=my_get)
```

The `Fetcher` and `Reply` types describe this, so a type checker can confirm your function fits. If your function raises one of the `requests` library's errors, such as a timeout, the package tries again just as it does for its own requests. Any other error is passed on to you.

## Field reference

### Fires

These are NOAA's columns as they come in the file, with the matching `HmsFire` field. The GeoJSON properties use NOAA's names exactly. NOAA renamed three columns in July 2022, so code written for older versions of this package needs the names in [What changed in this release](#what-changed-in-this-release).

| GeoJSON property | `HmsFire` field | What it means |
| --- | --- | --- |
| `Lat`, `Lon` | `latitude`, `longitude` | The center of the satellite pixel where a fire was detected, in degrees. Latitude is negative in the south and longitude is negative in the west. |
| `YearDay`, `Time` | `observed_at` | When the satellite took the image, in UTC. `YearDay` is the year and the day of the year, so `2026321` is the 321st day of 2026, November 17. `Time` is hours and minutes, like `0301`. The record joins them into one time. |
| `Satellite` | `satellite` | The satellite, as NOAA writes it. In a recent file: `NOAA 20` and `NOAA 21` (polar-orbiting, with the VIIRS camera), and `GOES-EAST` and `GOES-WEST` (fixed above the equator). Older files also had `SUOMI NPP` and `MODIS TERRA`. |
| `Method` | `method` | How the point was found. In a recent file: `VIIRS` and `NGFS` (automatic detections) and `ANALYSIS`. NOAA's page does not define these words. This package's author believes `ANALYSIS` marks a point an analyst added, and `NGFS` is a GOES detection method, but has not confirmed either. Older files also had `FDC` and `MODIS`. |
| `Ecosystem` | `ecosystem` | A number for the kind of land under the point. NOAA's page does not say what the numbers mean, and this package does not translate them. |
| `FRP` | `frp` | Fire radiative power, in megawatts: a measure of the heat a fire gives off, and a rough sign of how active it is. NOAA warns the values "can be significantly affected by imaging conditions". NOAA uses `-999` when it has no value, and the record turns that into `None`. |

### Smoke

| Column | `HmsSmoke` field | What it means |
| --- | --- | --- |
| geometry | `geometry` | The outline, as a GeoJSON polygon in longitude and latitude. |
| `Satellite` | `satellite` | The satellite whose images were used, such as `GOES-EAST` or `GOES-WEST`. |
| `Start`, `End` | `start`, `end` | The times of the images the outline covers, in UTC. NOAA writes them like `2026321 1300`: the year and day of the year, a space, then hours and minutes. |
| `Density` | `density` | `Light`, `Medium` or `Heavy`. This is how thick the smoke looks from above, as judged by an analyst. Before July 2022 NOAA wrote the numbers 5, 16 and 21 here, and this package no longer sees those. |

## What changed in this release

NOAA stopped updating the files this package used to download (`latesthms.txt` and `latest_smoke.*`) on July 18, 2022. Older versions of this package therefore returned fires and smoke from that day, no matter when you ran them. This version reads NOAA's current daily files instead, and `--date` and `date=` are new.

**The fire field names changed, because NOAA's file changed.** The package now gives you NOAA's column names as they come in the file. Three of them are different from the names older versions of this package returned:

| Old name | New name |
| --- | --- |
| `Method of Detect` | `Method` |
| `Ecosys` | `Ecosystem` |
| `Fire RadPower` | `FRP` |

`Lon`, `Lat`, `YearDay`, `Time` and `Satellite` are the same. The values changed too, because they are current: the satellites are now `NOAA 20`, `NOAA 21`, `GOES-EAST` and `GOES-WEST`, `Method` has a new value `NGFS`, and smoke `Density` is the word `Light`, `Medium` or `Heavy` instead of a number. In the typed records, the old `Fire RadPower` is `frp`.

**The old functions and commands are kept for existing code.** `get_hms_fires`, `get_hms_smoke`, `noaawildfires hms-fires` and `noaawildfires hms-smoke` work as before, with the same names and the same GeoJSON output shape, and they now carry the current data and the new field names above. Their docstrings say so. New code can use the typed records instead. No warning is printed when you use them.

The source of the files is `https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/`. The addresses look like `Fire_Points/Text/2026/11/hms_fire20261117.txt` and `Smoke_Polygons/Shapefile/2026/11/hms_smoke20261117.zip`.

## Credit and data terms

NOAA's HMS page does not give a credit line to copy, and this package's author did not find one. Credit NOAA, name the Hazard Mapping System, and read the notes at [ospo.noaa.gov/products/land/hms.html](https://www.ospo.noaa.gov/products/land/hms.html) and NOAA's disclaimer pages before you publish. Questions about the data go to NOAA's fire team at ssdfireteam@noaa.gov. This package only downloads the data. It is not made by NOAA and is not endorsed by NOAA.

## About this package

AI tools assisted in writing this package's code, tests and documentation. A person directed and reviewed the work.

## Contributing

Install dependencies for development.

```bash
uv sync --all-groups
```

Run the offline tests, the linter and the type checker.

```bash
make check
```

The tests that call NOAA's real website are skipped by default. Run them with `make test-live`.

## Developing the CLI

The command-line interface is implemented using Click. `uv sync` installs the package in editable form, so the `noaawildfires` command is ready to use with `uv run`.

```bash
uv run noaawildfires --help
```

## Other resources

* Issues: [github.com/datadesk/noaa-wildfires/issues](https://github.com/datadesk/noaa-wildfires/issues)
* Packaging: [pypi.python.org/pypi/noaa-wildfires](https://pypi.python.org/pypi/noaa-wildfires)
* Testing: [github.com/datadesk/noaa-wildfires/actions](https://github.com/datadesk/noaa-wildfires/actions)
