"""Investigative: extracts the stations on the Majlis Park <-> Deepali
Chowk Magenta Line stretch (still disconnected from the rest of Magenta --
the Krishna Park Extension <-> Deepali Chowk link is still under
construction) from ~/Downloads/delhi_metro_lines.geojson, in track order.
"""
import json
import math
import os

GEOJSON_PATH = os.path.expanduser("~/Downloads/delhi_metro_lines.geojson")
CLUSTER_THRESHOLD_M = 100


def haversine_m(lon1, lat1, lon2, lat2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


with open(GEOJSON_PATH) as f:
    data = json.load(f)

line = None
for feat in data["features"]:
    if feat["geometry"]["type"] == "LineString" and feat["properties"].get("ref") == "8":
        if "Majlis Park" in (feat["properties"].get("from") or ""):
            line = feat["geometry"]["coordinates"]
            break

points = []
for feat in data["features"]:
    if feat["geometry"]["type"] != "Point":
        continue
    rels = feat["properties"].get("@relations", [])
    if any("Majlis Park" in (r.get("reltags", {}).get("name") or "") and "Deepali Chowk" in (r.get("reltags", {}).get("name") or "") for r in rels):
        lon, lat = feat["geometry"]["coordinates"]
        points.append((lon, lat))

clusters = []
for lon, lat in points:
    placed = False
    for c in clusters:
        if haversine_m(lon, lat, c[0], c[1]) < CLUSTER_THRESHOLD_M:
            c[2] += 1
            c[0] += (lon - c[0]) / c[2]
            c[1] += (lat - c[1]) / c[2]
            placed = True
            break
    if not placed:
        clusters.append([lon, lat, 1])

def nearest_index(lon, lat):
    return min(range(len(line)), key=lambda i: haversine_m(lon, lat, line[i][0], line[i][1]))

ordered = sorted(clusters, key=lambda c: nearest_index(c[0], c[1]))

print(f"{len(points)} raw points -> {len(clusters)} distinct stations, in track order:")
for lon, lat, _ in ordered:
    print(f"  {lat:.6f}, {lon:.6f}")
