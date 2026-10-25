"""One-time extraction: finds the Pink Line stations missing from our GTFS
feed (the Majlis Park <-> Maujpur-Babarpur ring-closing extension, opened
2026-03-08) using the OSM export at ~/Downloads/delhi_metro_lines.geojson.

Read-only / investigative. Doesn't touch the GTFS feed. Prints the new
stations in track order so we can manually name them against what we
already know (Yamuna Vihar, Bhajanpura, Khajuri Khas, Soorghat, Sonia
Vihar, Jagatpur Village, Jharoda Majra, Burari) before writing anything.
"""
import csv
import json
import math
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
FEED_DIR = "app/src/main/assets/data/gtfs/metro"
CLUSTER_THRESHOLD_M = 100
KNOWN_STATION_THRESHOLD_M = 400


def haversine_m(lon1, lat1, lon2, lat2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


with open(GEOJSON_PATH) as f:
    data = json.load(f)

# every Point that's a stop of a Pink Line relation
pink_points = []
for feat in data["features"]:
    if feat["geometry"]["type"] != "Point":
        continue
    rels = feat["properties"].get("@relations", [])
    if any("Pink Line" in (r.get("reltags", {}).get("name") or "") for r in rels):
        lon, lat = feat["geometry"]["coordinates"]
        pink_points.append((lon, lat))

# cluster near-duplicate directional pairs into one station each
clusters = []  # list of [lon, lat] centroids, each built from member points
for lon, lat in pink_points:
    placed = False
    for cluster in clusters:
        clon, clat = cluster[0], cluster[1]
        if haversine_m(lon, lat, clon, clat) < CLUSTER_THRESHOLD_M:
            # merge: recompute centroid (cluster stores sum + count)
            cluster[2] += 1
            cluster[0] = clon + (lon - clon) / cluster[2]
            cluster[1] = clat + (lat - clat) / cluster[2]
            placed = True
            break
    if not placed:
        clusters.append([lon, lat, 1])

print(f"{len(pink_points)} raw points -> {len(clusters)} distinct stations after clustering")

# cross-reference against our existing stops.txt
known_coords = []
with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    lat_idx, lon_idx = header.index("stop_lat"), header.index("stop_lon")
    for row in reader:
        if row[lat_idx] and row[lon_idx]:
            known_coords.append((float(row[lon_idx]), float(row[lat_idx])))

new_stations = []
for clon, clat, _ in clusters:
    is_known = any(
        haversine_m(clon, clat, klon, klat) < KNOWN_STATION_THRESHOLD_M
        for klon, klat in known_coords
    )
    if not is_known:
        new_stations.append((clon, clat))

print(f"{len(new_stations)} stations not matched to anything already in our GTFS\n")

# order the new stations by their position along one Pink LineString
line = None
for feat in data["features"]:
    if feat["geometry"]["type"] == "LineString" and feat["properties"].get("ref") == "7":
        if "Shiv Vihar" in (feat["properties"].get("from") or ""):
            line = feat["geometry"]["coordinates"]
            break

def nearest_index_on_line(lon, lat):
    best_i, best_d = None, float("inf")
    for i, (plon, plat) in enumerate(line):
        d = haversine_m(lon, lat, plon, plat)
        if d < best_d:
            best_d, best_i = d, i
    return best_i

ordered = sorted(new_stations, key=lambda s: nearest_index_on_line(s[0], s[1]))

print("New stations, in track order (lon, lat):")
for lon, lat in ordered:
    print(f"  {lon:.6f}, {lat:.6f}")
