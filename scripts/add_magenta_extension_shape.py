"""One-time fix: points the Majlis Park <-> Deepali Chowk Magenta
extension trip at its real OSM track geometry, so it renders on the map
as its own distinct shape alongside the main Botanical Garden <-> Krishna
Park Extension stretch.
"""
import csv
import json
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
FEED_DIR = "app/src/main/assets/data/gtfs/metro"
NEW_SHAPE_ID = "shp_magenta_ext"

with open(GEOJSON_PATH) as f:
    data = json.load(f)

line = None
for feat in data["features"]:
    if feat["geometry"]["type"] == "LineString" and feat["properties"].get("ref") == "8":
        if "Majlis Park" in (feat["properties"].get("from") or ""):
            line = feat["geometry"]["coordinates"]
            break

if line is None:
    raise SystemExit("Could not find the Majlis Park -> Deepali Chowk relation")

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
    if row[trip_idx] == "magenta_ext_fwd_1":
        row[shape_idx] = NEW_SHAPE_ID
        repointed = True
        break

if not repointed:
    raise SystemExit("Could not find magenta_ext_fwd_1 trip")

with open(f"{FEED_DIR}/trips.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("Repointed magenta_ext_fwd_1 to the new shape")
