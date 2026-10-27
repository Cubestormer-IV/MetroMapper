"""One-time correction pass using OSM's station data
(~/Downloads/delhi_metro_stations.geojson):

1. Platform children (e.g. "100_green") get their OWN real per-line
   coordinate from OSM's line-tagged node for that station (e.g.
   "Kirti Nagar (Green Line)"), instead of just copying their parent's
   single point -- matched by proximity to the child's current
   coordinate plus the line name appearing in the OSM name, never by
   exact string match (station names differ in formatting too often to
   trust that).
2. Each interchange parent's own coordinate is then set to the average
   of its (now corrected) children, as the one representative point the
   app shows for that Place.
3. Plain, non-split stations get corrected directly from the nearest
   OSM station within 300m, same technique used for Bhikaji Cama Place,
   Lajpat Nagar, etc. earlier this session.

Nothing is changed where no confident OSM match exists -- left as the
existing (possibly still-imprecise) value rather than guessed at.

Not idempotent -- not meant to be re-run against its own output.
"""
import csv
import json
import math
import os
from collections import defaultdict

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
OSM_PATH = os.path.expanduser("~/Downloads/delhi_metro_stations.geojson")

LINE_NAME_FRAGMENT = {
    "red": "Red Line",
    "yellow": "Yellow Line",
    "blue": "Blue Line",
    "green": "Green Line",
    "violet": "Violet Line",
    "pink": "Pink Line",
    "magenta": "Magenta Line",
    "gray": "Grey Line",
    "orange": "Airport Express",
}

PLATFORM_MATCH_RADIUS_M = 600
PLAIN_MATCH_RADIUS_M = 300


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


with open(OSM_PATH) as f:
    osm_data = json.load(f)

osm_points = []  # (name, lat, lon)
for feat in osm_data["features"]:
    name = feat["properties"].get("name")
    if not name:
        continue
    lon, lat = feat["geometry"]["coordinates"]
    osm_points.append((name, lat, lon))

with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

i_id = header.index("stop_id")
i_lat = header.index("stop_lat")
i_lon = header.index("stop_lon")
i_loc = header.index("location_type")
i_parent = header.index("parent_station")

platform_fixed = 0
plain_fixed = 0
children_by_parent = defaultdict(list)

for row in rows:
    if row[i_parent]:
        # platform child -- line id is the stop_id's suffix after the last "_"
        line_id = row[i_id].rsplit("_", 1)[-1]
        fragment = LINE_NAME_FRAGMENT.get(line_id)
        cur_lat, cur_lon = float(row[i_lat]), float(row[i_lon])

        if fragment:
            candidates = [
                (lat, lon) for name, lat, lon in osm_points
                if fragment in name and haversine_m(cur_lat, cur_lon, lat, lon) < PLATFORM_MATCH_RADIUS_M
            ]
            if candidates:
                best = min(candidates, key=lambda c: haversine_m(cur_lat, cur_lon, c[0], c[1]))
                row[i_lat], row[i_lon] = str(best[0]), str(best[1])
                platform_fixed += 1

        children_by_parent[row[i_parent]].append(row)

for row in rows:
    cur_lat, cur_lon = float(row[i_lat]), float(row[i_lon])

    if row[i_loc] == "1":
        # interchange parent -- average its (now corrected) children
        children = children_by_parent[row[i_id]]
        avg_lat = sum(float(c[i_lat]) for c in children) / len(children)
        avg_lon = sum(float(c[i_lon]) for c in children) / len(children)
        row[i_lat], row[i_lon] = str(avg_lat), str(avg_lon)
        continue

    if row[i_parent]:
        continue  # already handled above

    # plain, non-split station
    best = min(osm_points, key=lambda o: haversine_m(cur_lat, cur_lon, o[1], o[2]))
    dist = haversine_m(cur_lat, cur_lon, best[1], best[2])
    if dist < PLAIN_MATCH_RADIUS_M and dist > 1:  # >1m so we don't "fix" already-correct rows
        row[i_lat], row[i_lon] = str(best[1]), str(best[2])
        plain_fixed += 1

with open(f"{FEED_DIR}/stops.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print(f"platform children corrected with real per-line coordinates: {platform_fixed}")
print(f"plain stations corrected: {plain_fixed}")
