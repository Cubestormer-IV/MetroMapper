"""One-time fix: Green Line's Ashok Park Main <-> Kirti Nagar spur is
already correctly routable (it's real trip data, not synthetic), but
isn't rendered on the map -- no trip's shape_id points at the spur's own
geometry, only at the trunk's. Repoints one real trip that actually
passes through Kirti Nagar (4119) at the spur's real OSM track shape.
"""
import csv
import json
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
FEED_DIR = "app/src/main/assets/data/gtfs/metro"
NEW_SHAPE_ID = "shp_osm_5_spur"
TRIP_ID = "4119"

with open(GEOJSON_PATH) as f:
    data = json.load(f)

line = None
for feat in data["features"]:
    if feat["geometry"]["type"] == "LineString" and feat["properties"].get("ref") == "5":
        name = feat["properties"].get("name") or ""
        if "Kirti Nagar" in name and "Ashok Park Main" in name:
            line = feat["geometry"]["coordinates"]
            break

if line is None:
    raise SystemExit("Could not find the Ashok Park Main <-> Kirti Nagar relation")

with open(f"{FEED_DIR}/shapes.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for seq, (lon, lat) in enumerate(line, start=1):
        writer.writerow([NEW_SHAPE_ID, lat, lon, seq, ""])

print(f"Appended {len(line)} shape points as {NEW_SHAPE_ID}")

with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [header] + list(reader)

trip_idx = header.index("trip_id")
shape_idx = header.index("shape_id")
repointed = False
for row in rows[1:]:
    if row[trip_idx] == TRIP_ID:
        row[shape_idx] = NEW_SHAPE_ID
        repointed = True
        break

if not repointed:
    raise SystemExit(f"Could not find trip {TRIP_ID}")

with open(f"{FEED_DIR}/trips.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"Repointed trip {TRIP_ID} to the new shape")
