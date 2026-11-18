# noaa-wildfires

Download wildfire detections and smoke outlines from NOAA's [Hazard Mapping System](https://www.ospo.noaa.gov/products/land/hms.html), as GeoJSON or typed Python records.

**A fire detection is a hot spot seen by a satellite. It is not a confirmed wildfire.** Industrial heat, gas flares, reflections and false alarms show up too. A smoke outline is where an analyst saw smoke from space, not a measure of the air near the ground.

## Install

```sh
uv add noaa-wildfires
```

## Use it from the command line

```sh
noaawildfires hms-fires > fires.json
noaawildfires hms-smoke --date 2026-11-17
```

## Use it from Python

```python
import noaa_wildfires

data = noaa_wildfires.get_hms_fires()  # GeoJSON, latest day
fires = noaa_wildfires.get_hms_fire_records("2026-11-17")  # typed records
print(fires[0].observed_at, fires[0].frp)
smoke = noaa_wildfires.get_hms_smoke_records()
```

With no date, the package reads today's file and falls back up to three days if it is empty. Pass `date="2026-11-17"` for a single day. You can also pass `get=` with your own web request function, and `timeout=` to wait longer for NOAA.

## Things to know

* **Detections are not confirmed wildfires.** NOAA says the fire points "should be used as general guidance", and that decisions to fight fires or evacuate "should not be made without other information to corroborate the fire's existence and location."
* **Older versions returned old data.** NOAA stopped updating the files they read on July 18, 2022. This version reads NOAA's current daily files.
* **Three fire field names changed, because NOAA's file changed.** `Method of Detect` is now `Method`, `Ecosys` is `Ecosystem` and `Fire RadPower` is `FRP`. The old functions and commands still work and now return the new names.
* **Downloads retry.** A request waits 60 seconds, then tries again on network errors and server errors, and raises `noaa_wildfires.NOAAError` if it still fails.
* **The data comes from NOAA.** This package is not made or endorsed by NOAA. The code is MIT.
* **AI helped write this package.** AI tools assisted in writing its code, tests and documentation. A person directed and reviewed the work.

The documentation has the field reference and what NOAA says about the data.

This repository's full history is large (GitHub reports about 133 MB, across more than 2,700 commits), because the scraped data files were saved to it for years. Copy only the latest version:

```bash
git clone --depth 1 https://github.com/datadesk/noaa-wildfires.git
```

### Links

* Docs: [palewi.re/docs/noaa-wildfires/](https://palewi.re/docs/noaa-wildfires/)
* Issues: [github.com/datadesk/noaa-wildfires/issues](https://github.com/datadesk/noaa-wildfires/issues)
* Packaging: [pypi.python.org/pypi/noaa-wildfires](https://pypi.python.org/pypi/noaa-wildfires)
* Testing: [github.com/datadesk/noaa-wildfires/actions](https://github.com/datadesk/noaa-wildfires/actions)
