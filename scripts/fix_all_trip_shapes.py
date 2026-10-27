"""Fixes a bug in the earlier shape-fixing scripts: they only repointed
one representative trip per route to the correct OSM-derived shape,
leaving every other trip of that same route still pointing at the old
(rough) bundled shape -- so the map rendered both the new correct line
and the old wrong one overlapping. Repoints every trip, splitting Green
and Magenta's trips between trunk and spur shape based on which stops
each trip actually visits (not just picking one sample trip per group).
"""
import csv

FEED_DIR = "app/src/main/assets/data/gtfs/metro"

# route_id -> single correct shape_id for every trip
SINGLE_SHAPE_ROUTES = {
    "Delhi1": "shp_osm_1",
    "Delhi2": "shp_osm_2",
    "Delhi3": "shp_osm_3",
    "Delhi4": "shp_osm_4",
    "Delhi6": "shp_osm_6",
    "Delhi7": "shp_pink_ring",
    "Delhi9": "shp_osm_9",
    "DelhiAirport": "shp_osm_AEx",
}

# route_id -> (set of stop_ids that mark a trip as the "spur", spur shape_id, trunk shape_id)
SPLIT_SHAPE_ROUTES = {
    "Delhi5": ({"satguru_ram_singh_marg", "100_green"}, "shp_osm_5_spur", "shp_osm_5"),
    "Delhi8": (
        {"529", "530", "531", "532", "533", "534", "173_magenta"},
        "shp_magenta_ext",
        "shp_osm_8",
    ),
}

with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [header] + list(reader)

route_idx = header.index("route_id")
trip_idx = header.index("trip_id")
shape_idx = header.index("shape_id")

stops_of_trip = {}
with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
    reader = csv.reader(f)
    st_header = next(reader)
    st_trip_idx = st_header.index("trip_id")
    st_stop_idx = st_header.index("stop_id")
    for row in reader:
        stops_of_trip.setdefault(row[st_trip_idx], set()).add(row[st_stop_idx])

counts = {}
for row in rows[1:]:
    route_id = row[route_idx]
    trip_id = row[trip_idx]

    if route_id in SINGLE_SHAPE_ROUTES:
        row[shape_idx] = SINGLE_SHAPE_ROUTES[route_id]
    elif route_id in SPLIT_SHAPE_ROUTES:
        marker_stops, spur_shape, trunk_shape = SPLIT_SHAPE_ROUTES[route_id]
        is_spur = bool(stops_of_trip.get(trip_id, set()) & marker_stops)
        row[shape_idx] = spur_shape if is_spur else trunk_shape
    else:
        continue

    counts[row[shape_idx]] = counts.get(row[shape_idx], 0) + 1

with open(f"{FEED_DIR}/trips.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

for shape_id, n in sorted(counts.items()):
    print(f"{shape_id}: {n} trips")
