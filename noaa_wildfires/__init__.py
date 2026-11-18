import csv
import io

import requests
import shapefile
from geojson import Feature, FeatureCollection, Point


def get_hms_fires():
    """
    Get the latest fires from Hazard Mapping System satellites.
    """
    # Read CSV
    r = requests.get("https://satepsanone.nesdis.noaa.gov/pub/FIRE/HMS/latesthms.txt")
    lines = r.content.decode("utf-8").splitlines()
    reader = csv.DictReader(lines, delimiter=",")

    # Tidy it up
    tidy_reader = []
    for row in reader:
        tidy_row = {k.strip(): v.strip() for k, v in row.items()}
        tidy_reader.append(tidy_row)

    # Convert it to GeoJSON
    features = [
        Feature(geometry=Point(map(float, [r["Lon"], r["Lat"]])), properties=r)
        for r in tidy_reader
    ]

    # Return it
    return FeatureCollection(features)


def get_hms_smoke():
    """
    Get the latest smoke data from Hazard Mapping System satellites.
    """
    files = ["latest_smoke.shp", "latest_smoke.dbf", "latest_smoke.shx"]
    return _parse_shapefiles(files)


def _parse_shapefiles(files):
    """
    Download the provided list of shapefile components and convert them to GeoJSON.
    """
    # Download each piece of the shapefile
    pieces = {}
    for name in files:
        r = requests.get(f"https://satepsanone.nesdis.noaa.gov/pub/FIRE/HMS/GIS/{name}")
        pieces[name.rsplit(".", 1)[-1]] = bytes(r.content)

    # Read the shapefile and convert it to GeoJSON
    return _read_shapefile(pieces["shp"], pieces["shx"], pieces["dbf"])


def _read_shapefile(shp, shx, dbf):
    """
    Convert the bytes of a shapefile's three main pieces to GeoJSON.

    Each feature keeps the odd shape it has always had: its properties hold a
    copy of the whole feature, with the attributes inside under "properties".
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


def _round(value):
    """
    Round every coordinate to the six decimal places NOAA publishes.
    """
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    return value
