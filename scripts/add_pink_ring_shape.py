"""One-time fix: Pink Line's shapes.txt entry (shp_1_35) predates the
2026-03-08 ring closure and doesn't include the Majlis Park <-> Maujpur
stretch, so the map's background polyline is missing it even though
routing/canonical data already has it. Replaces it with the real,
already-correct ring geometry from OpenStreetMap
(~/Downloads/delhi_metro_lines.geojson), and repoints the one Pink Line
trip the map actually reads (the first one in trips.txt) at the new shape.
"""
import csv
import json
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
FEED_DIR = "app/src/main/assets/data/gtfs/metro"
NEW_SHAPE_ID = "shp_pink_ring"

with open(GEOJSON_PATH) as f:
    data = json.load(f)

line = None
for feat in data["features"]:
    if feat["geometry"]["type"] == "LineString" and feat["properties"].get("ref") == "7":
        if "Shiv Vihar" in (feat["properties"].get("from") or ""):
            line = feat["geometry"]["coordinates"]
            break

if line is None:
    raise SystemExit("Could not find the Pink Line relation in the GeoJSON")

with open(f"{FEED_DIR}/shapes.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for seq, (lon, lat) in enumerate(line, start=1):
        writer.writerow([NEW_SHAPE_ID, lat, lon, seq, ""])

print(f"Appended {len(line)} shape points as {NEW_SHAPE_ID}")

# repoint the trip the map renderer actually picks (first Delhi7 row in file order)
rows = []
with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [header] + list(reader)

route_idx = header.index("route_id")
shape_idx = header.index("shape_id")
repointed = False
for row in rows[1:]:
    if row[route_idx] == "Delhi7" and not repointed:
        row[shape_idx] = NEW_SHAPE_ID
        repointed = True
        break

if not repointed:
    raise SystemExit("Could not find a Delhi7 trip to repoint")

with open(f"{FEED_DIR}/trips.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("Repointed the first Delhi7 trip to the new shape")
