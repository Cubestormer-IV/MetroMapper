"""Replaces shapes.txt geometry for every metro line (except Pink, already
fixed) with the real track geometry from OpenStreetMap
(~/Downloads/delhi_metro_lines.geojson), and repoints each line's
representative trip (the one MainActivity.loadMetroLineShapes actually
renders -- the first trip per route_id in trips.txt) at the new shape.

For a line whose OSM data has more than one physically distinct
relation (a branch, like Green and Magenta), only one shape can be shown
today since the app renders a single polyline per route_id -- picks the
relation with the most points (the trunk) and leaves the spur/extension
unrendered on the map background; routing is unaffected either way.
Gurgaon Rapid Metro and Noida Aqua Line aren't tagged under OSM's "Delhi
Metro" network, so they're left alone.
"""
import csv
import json
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
FEED_DIR = "app/src/main/assets/data/gtfs/metro"

ROUTE_ID_TO_OSM_REF = {
    "Delhi1": "1",   # Red
    "Delhi2": "2",   # Yellow
    "Delhi3": "3",   # Blue trunk (Dwarka <-> Noida Electronic City)
    "Delhi4": "4",   # Blue Vaishali branch
    "Delhi5": "5",   # Green (trunk only -- Kirti Nagar spur won't render)
    "Delhi6": "6",   # Violet
    "Delhi8": "8",   # Magenta (trunk only -- Majlis Park extension won't render)
    "Delhi9": "9",   # Grey
    "DelhiAirport": "AEx",
}

with open(GEOJSON_PATH) as f:
    data = json.load(f)

# best (most points) LineString per ref
best_by_ref = {}
for feat in data["features"]:
    if feat["geometry"]["type"] != "LineString":
        continue
    ref = feat["properties"].get("ref")
    coords = feat["geometry"]["coordinates"]
    if ref not in best_by_ref or len(coords) > len(best_by_ref[ref]):
        best_by_ref[ref] = coords

with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [header] + list(reader)

route_idx = header.index("route_id")
shape_idx = header.index("shape_id")

new_shapes = []  # (shape_id, [[lat, lon], ...])
repointed = set()

for row in rows[1:]:
    route_id = row[route_idx]
    if route_id in repointed or route_id not in ROUTE_ID_TO_OSM_REF:
        continue
    ref = ROUTE_ID_TO_OSM_REF[route_id]
    coords = best_by_ref.get(ref)
    if coords is None:
        print(f"WARNING: no OSM relation found for {route_id} (ref {ref}), skipping")
        continue

    shape_id = f"shp_osm_{ref}"
    row[shape_idx] = shape_id
    new_shapes.append((shape_id, coords))
    repointed.add(route_id)

with open(f"{FEED_DIR}/trips.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

with open(f"{FEED_DIR}/shapes.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for shape_id, coords in new_shapes:
        for seq, (lon, lat) in enumerate(coords, start=1):
            writer.writerow([shape_id, lat, lon, seq, ""])

print(f"Repointed {len(repointed)} routes: {sorted(repointed)}")
missing = set(ROUTE_ID_TO_OSM_REF) - repointed
if missing:
    print(f"Not repointed (no matching trip found in trips.txt?): {sorted(missing)}")
