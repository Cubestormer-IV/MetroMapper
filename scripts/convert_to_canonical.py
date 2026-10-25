"""
Converts the bundled GTFS feeds (app/src/main/assets/data/gtfs/{metro,bus}/)
into MetroMapper's canonical JSON (app/src/main/assets/data/canonical/).

Metro output: stations.json, lines.json, connections.json, transfers.json.
Bus output: bus_stations.json, bus_lines.json, bus_connections.json — kept
separate since bus is ~100x the size of metro and nothing routes on it yet.

termini.json is hand-maintained and is not touched by this script.

Station (Place) IDs are slugified names, same as always, so termini.json's
"line:stationId" keys keep working. Since split_interchange_platforms.py,
some stops have a parent_station — those get a finer routing-node id,
"<placeId>:<line>", so a change of line at an interchange is a move between
distinct graph nodes, not invisible. connections.json's from/to use these
node ids; stations.json's ids are always the coarser Place id.
"""

import csv
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "app/src/main/assets/data"
GTFS_METRO = DATA / "gtfs/metro"
GTFS_BUS = DATA / "gtfs/bus"
OUTPUT = DATA / "canonical"

# Metro's route_id -> canonical line id. Blue and Green's branches collapse
# to one line id each (branches are handled by termini.json, not by having
# two line ids) because that's inconsistent in the source: DMRC splits Blue
# into two routes but keeps Green as one route with multiple trip patterns.
METRO_LINE_FOR_ROUTE = {
    "Delhi1": "red",
    "Delhi2": "yellow",
    "Delhi3": "blue",
    "Delhi4": "blue",
    "Delhi5": "green",
    "Delhi6": "violet",
    "Delhi7": "pink",
    "Delhi8": "magenta",
    "Delhi9": "gray",
    "DelhiAirport": "orange",
    "Gurgaon1": "rapid",
    "NoidaAqua": "aqua",
}

METRO_LINE_NAME = {
    "red": "Red Line",
    "yellow": "Yellow Line",
    "blue": "Blue Line",
    "green": "Green Line",
    "violet": "Violet Line",
    "pink": "Pink Line",
    "magenta": "Magenta Line",
    "gray": "Gray Line",
    "orange": "Orange Line",
    "rapid": "Rapid Metro",
    "aqua": "Aqua Line",
}

BUS_LINE_COLOR = "#616161"  # bus routes.txt has no route_color column


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        index = {name: i for i, name in enumerate(header)}
        return index, list(reader)


def station_id(name):
    """Turn a station name into a stable ID. Must match the slugs
    termini.json already uses — do not change this lightly."""
    return (
        name.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("'", "")
    )


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def gtfs_time_to_seconds(value):
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def process_feed(feed_dir, mode, route_to_line, stations, lines, connections):
    """Shared pipeline for one GTFS feed. Mutates stations/lines/connections
    in place. Returns node_of_stop, so callers can translate a raw stop_id
    (e.g. from transfers.txt) into the same node ids connections use."""

    stops_idx, stops_rows = read_rows(feed_dir / "stops.txt")
    trips_idx, trips_rows = read_rows(feed_dir / "trips.txt")
    st_idx, st_rows = read_rows(feed_dir / "stop_times.txt")

    has_dist = "shape_dist_traveled" in st_idx
    has_parent = "parent_station" in stops_idx

    # trip_id -> line id (needed below, and again for the main pass)
    line_of_trip = {}
    for row in trips_rows:
        route_id = row[trips_idx["route_id"]]
        trip_id = row[trips_idx["trip_id"]]
        line_id = route_to_line(route_id)
        if line_id:
            line_of_trip[trip_id] = line_id

    # which line(s) actually use each raw stop_id — only needed to name split
    # platforms, so skip the work entirely for feeds that have none (bus)
    lines_of_stop = {}
    if has_parent:
        for row in st_rows:
            line_id = line_of_trip.get(row[st_idx["trip_id"]])
            if line_id:
                lines_of_stop.setdefault(row[st_idx["stop_id"]], set()).add(line_id)

    # stop_id -> place id (the Place/station — always the coarse, name-based id)
    # stop_id -> node id (the routing graph node — finer at split platforms)
    place_of_stop = {}
    node_of_stop = {}

    for row in stops_rows:
        stop_id = row[stops_idx["stop_id"]]
        name = row[stops_idx["stop_name"]].strip()
        lat = float(row[stops_idx["stop_lat"]])
        lon = float(row[stops_idx["stop_lon"]])

        place_id = station_id(name) if mode == "metro" else f"bus:{stop_id}"
        place_of_stop[stop_id] = place_id

        parent = row[stops_idx["parent_station"]] if has_parent else ""
        if parent:
            line_id = next(iter(lines_of_stop.get(stop_id, ())), None)
            node_of_stop[stop_id] = f"{place_id}:{line_id}" if line_id else place_id
        else:
            node_of_stop[stop_id] = place_id

        if place_id not in stations:
            stations[place_id] = {
                "id": place_id,
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "lines": [],
            }

    # group stop_times by trip, in file order, then sort each group by sequence
    stop_times_by_trip = {}
    for row in st_rows:
        trip_id = row[st_idx["trip_id"]]
        stop_times_by_trip.setdefault(trip_id, []).append(row)

    best = {}  # (from_node, to_node, line) -> (distance_m, duration_s)

    for trip_id, rows in stop_times_by_trip.items():
        line_id = line_of_trip.get(trip_id)
        if not line_id:
            continue

        rows.sort(key=lambda r: int(r[st_idx["stop_sequence"]]))

        for a, b in zip(rows, rows[1:]):
            a_stop, b_stop = a[st_idx["stop_id"]], b[st_idx["stop_id"]]
            from_node, to_node = node_of_stop.get(a_stop), node_of_stop.get(b_stop)
            from_place, to_place = place_of_stop.get(a_stop), place_of_stop.get(b_stop)

            if not from_node or not to_node or from_node == to_node:
                continue

            duration_s = gtfs_time_to_seconds(
                b[st_idx["arrival_time"]]
            ) - gtfs_time_to_seconds(a[st_idx["departure_time"]])

            if duration_s <= 0:
                continue  # bad data (e.g. midnight rollover) — skip, don't fake a weight

            if has_dist:
                distance_m = abs(
                    float(b[st_idx["shape_dist_traveled"]])
                    - float(a[st_idx["shape_dist_traveled"]])
                )
            else:
                distance_m = haversine_m(
                    stations[from_place]["latitude"], stations[from_place]["longitude"],
                    stations[to_place]["latitude"], stations[to_place]["longitude"],
                )

            if distance_m <= 0:
                continue  # same fix as the zero-distance bug, applied at the source

            for place_id in (from_place, to_place):
                if line_id not in stations[place_id]["lines"]:
                    stations[place_id]["lines"].append(line_id)

            key = (from_node, to_node, line_id)
            candidate = (round(distance_m), round(duration_s))

            if key not in best or candidate[1] < best[key][1]:
                best[key] = candidate

    for (from_node, to_node, line_id), (distance_m, duration_s) in best.items():
        connections[(from_node, to_node, line_id)] = {
            "from": from_node,
            "to": to_node,
            "line": line_id,
            "mode": mode,
            "distance_m": distance_m,
            "duration_s": duration_s,
        }

    return node_of_stop


def derive_transfers(feed_dir, node_of_stop):
    path = feed_dir / "transfers.txt"
    if not path.exists():
        return []

    idx, rows = read_rows(path)
    transfers = []

    for row in rows:
        from_node = node_of_stop.get(row[idx["from_stop_id"]])
        to_node = node_of_stop.get(row[idx["to_stop_id"]])
        if not from_node or not to_node or from_node == to_node:
            continue
        transfers.append({
            "from": from_node,
            "to": to_node,
            "duration_s": int(row[idx["min_transfer_time"]]),
        })

    return transfers


# Wye junctions: a rider can continue freely from the trunk to either
# branch, but switching between the two branches requires a real platform
# change. Each junction's plain node is split into two copies (:A, :B); the
# trunk's edge is duplicated to both, each branch's edge is retargeted to
# its own copy, and a Walk edge (same ~5min + noise placeholder used for
# interchange transfers, since there's no real walk-time data for these
# either) connects the two copies. Found by riding them -- not detectable
# from the schedule data alone, since each one still only has 2 distinct
# neighbors in any single trip.
WYE_JUNCTIONS = [
    # (junction_name, trunk_name, branchA_name, branchB_name)
    ("Ashok Park Main", "Punjabi Bagh", "Inderlok", "Satguru Ram Singh Marg"),
    ("Yamuna Bank", "Indraprastha", "Laxmi Nagar", "Akshardham"),
    ("Maujpur - Babarpur", "Jafrabad", "Yamuna Vihar", "Gokulpuri"),
]


def place_of(node_id):
    return node_id.split(":")[0]


def split_wye_junctions(stations, connections, transfers):
    name_to_id = {s["name"]: s["id"] for s in stations.values()}
    rng = random.Random(11)

    for junction_name, trunk_name, a_name, b_name in WYE_JUNCTIONS:
        junction_id = name_to_id[junction_name]
        trunk_id = name_to_id[trunk_name]
        a_id = name_to_id[a_name]
        b_id = name_to_id[b_name]

        junction_a = f"{junction_id}:A"
        junction_b = f"{junction_id}:B"

        touching = [c for c in connections.values() if junction_id in (c["from"], c["to"])]

        def retarget(edge, new_junction_node):
            e = dict(edge)
            if e["from"] == junction_id:
                e["from"] = new_junction_node
            else:
                e["to"] = new_junction_node
            return e

        for c in touching:
            del connections[(c["from"], c["to"], c["line"])]
            other = c["to"] if c["from"] == junction_id else c["from"]
            other_place = place_of(other)

            if other_place == trunk_id:
                for copy in (retarget(c, junction_a), retarget(c, junction_b)):
                    connections[(copy["from"], copy["to"], copy["line"])] = copy
            elif other_place == a_id:
                copy = retarget(c, junction_a)
                connections[(copy["from"], copy["to"], copy["line"])] = copy
            elif other_place == b_id:
                copy = retarget(c, junction_b)
                connections[(copy["from"], copy["to"], copy["line"])] = copy
            else:
                raise ValueError(f"Unexpected neighbor {other} at junction {junction_name}")

        duration_s = max(60, round(rng.gauss(300, 60)))
        transfers.append({"from": junction_a, "to": junction_b, "duration_s": duration_s})
        transfers.append({"from": junction_b, "to": junction_a, "duration_s": duration_s})


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_metro():
    stations, lines, connections = {}, {}, {}

    routes_idx, routes_rows = read_rows(GTFS_METRO / "routes.txt")
    color_of_line = {}
    for row in routes_rows:
        route_id = row[routes_idx["route_id"]]
        line_id = METRO_LINE_FOR_ROUTE.get(route_id)
        if line_id and line_id not in color_of_line:
            color_of_line[line_id] = "#" + row[routes_idx["route_color"]]

    for line_id, name in METRO_LINE_NAME.items():
        lines[line_id] = {
            "id": line_id,
            "name": name,
            "color": color_of_line.get(line_id, "#9E9E9E"),
            "mode": "metro",
        }

    node_of_stop = process_feed(
        GTFS_METRO, "metro",
        lambda route_id: METRO_LINE_FOR_ROUTE.get(route_id),
        stations, lines, connections,
    )

    transfers = derive_transfers(GTFS_METRO, node_of_stop)
    split_wye_junctions(stations, connections, transfers)

    write_json(OUTPUT / "stations.json", sorted(stations.values(), key=lambda s: s["id"]))
    write_json(OUTPUT / "lines.json", sorted(lines.values(), key=lambda l: l["id"]))
    write_json(
        OUTPUT / "connections.json",
        sorted(connections.values(), key=lambda c: (c["from"], c["to"], c["line"])),
    )
    write_json(
        OUTPUT / "transfers.json",
        sorted(transfers, key=lambda t: (t["from"], t["to"])),
    )

    print(f"metro: {len(stations)} stations, {len(lines)} lines, "
          f"{len(connections)} connections, {len(transfers)} transfers")


def run_bus():
    stations, lines, connections = {}, {}, {}

    routes_idx, routes_rows = read_rows(GTFS_BUS / "routes.txt")
    name_of_route = {}
    for row in routes_rows:
        route_id = row[routes_idx["route_id"]]
        name = row[routes_idx["route_long_name"]].strip() or row[routes_idx["route_short_name"]].strip()
        name_of_route[route_id] = name or route_id

    def route_to_line(route_id):
        return f"bus:{route_id}"

    process_feed(GTFS_BUS, "bus", route_to_line, stations, lines, connections)

    # only emit lines that actually got used in a connection
    used_line_ids = {c["line"] for c in connections.values()}
    for line_id in used_line_ids:
        route_id = line_id.removeprefix("bus:")
        lines[line_id] = {
            "id": line_id,
            "name": name_of_route.get(route_id, route_id),
            "color": BUS_LINE_COLOR,
            "mode": "bus",
        }

    write_json(OUTPUT / "bus_stations.json", sorted(stations.values(), key=lambda s: s["id"]))
    write_json(OUTPUT / "bus_lines.json", sorted(lines.values(), key=lambda l: l["id"]))
    write_json(
        OUTPUT / "bus_connections.json",
        sorted(connections.values(), key=lambda c: (c["from"], c["to"], c["line"])),
    )

    print(f"bus: {len(stations)} stops, {len(lines)} routes, {len(connections)} connections")


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    run_metro()
    run_bus()
