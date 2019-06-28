import os
import csv
import fiona
import requests
from geojson import Feature, FeatureCollection, Point


def get_hms_fires():
    """
    Get the latest fires from Hazard Mapping System satellites.
    """
    # Read CSV
    r = requests.get("https://satepsanone.nesdis.noaa.gov/pub/FIRE/HMS/latesthms.txt")
    lines = r.content.decode('utf-8').splitlines()
    reader = csv.DictReader(lines, delimiter=',')

    # Tidy it up
    tidy_reader = []
    for row in reader:
        tidy_row = dict((k.strip(), v.strip()) for k, v in row.items())
        tidy_reader.append(tidy_row)

    # Convert it to GeoJSON
    features = [Feature(
        geometry=Point(map(float, [r['Lon'], r['Lat']])),
        properties=r
    ) for r in tidy_reader]

    # Return it
    return FeatureCollection(features)


def get_hms_smoke():
    """
    Get the latest smoke data from Hazard Mapping System satellites.
    """
    files = [
        'latest_smoke.shp',
        'latest_smoke.dbf',
        'latest_smoke.shx'
    ]
    return _parse_shapefiles(files)


def _parse_shapefiles(files):
    # Download shapefiles
    for name in files:
        r = requests.get(f"https://satepsanone.nesdis.noaa.gov/pub/FIRE/HMS/GIS/{name}")
        with open(name, 'wb') as f:
            f.write(r.content)

    # Parse shapefiles
    f = fiona.open(files[0])

    # Create GeoJSON
    collection = FeatureCollection([Feature(geometry=d['geometry'], properties=d) for d in f])

    # Remove files
    [os.remove(name) for name in files]

    # Return data
    return collection
