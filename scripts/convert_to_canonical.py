"""
Converts the bundled GTFS feeds (app/src/main/assets/data/gtfs/{metro,bus}/)
into MetroMapper's canonical JSON (app/src/main/assets/data/canonical/).

Metro output: stations.json, lines.json, connections.json (same files the
app already reads; new fields are additive, Gson ignores unknown ones).
Bus output: bus_stations.json, bus_lines.json, bus_connections.json — kept
separate since bus is ~100x the size of metro and nothing routes on it yet.

termini.json is hand-maintained and is not touched by this script. Station
IDs for metro are generated the same way as before (slugified name) so
termini.json's existing "line:stationId" keys keep working.
"""

import csv
import json
import math
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
    in place so metro and bus can write into the same structures before
    being split into separate output files by the caller."""

    stops_idx, stops_rows = read_rows(feed_dir / "stops.txt")
    trips_idx, trips_rows = read_rows(feed_dir / "trips.txt")
    st_idx, st_rows = read_rows(feed_dir / "stop_times.txt")

    has_dist = "shape_dist_traveled" in st_idx

    # stop_id -> place id, and place id -> station record
    place_of_stop = {}
    for row in stops_rows:
        stop_id = row[stops_idx["stop_id"]]
        name = row[stops_idx["stop_name"]].strip()
        lat = float(row[stops_idx["stop_lat"]])
        lon = float(row[stops_idx["stop_lon"]])

        place_id = station_id(name) if mode == "metro" else f"bus:{stop_id}"
        place_of_stop[stop_id] = place_id

        if place_id not in stations:
            stations[place_id] = {
                "id": place_id,
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "lines": [],
            }

    # trip_id -> line id
    line_of_trip = {}
    for row in trips_rows:
        route_id = row[trips_idx["route_id"]]
        trip_id = row[trips_idx["trip_id"]]
        line_id = route_to_line(route_id)
        if line_id:
            line_of_trip[trip_id] = line_id

    # group stop_times by trip, in file order, then sort each group by sequence
    stop_times_by_trip = {}
    for row in st_rows:
        trip_id = row[st_idx["trip_id"]]
        stop_times_by_trip.setdefault(trip_id, []).append(row)

    best = {}  # (from, to, line) -> (distance_m, duration_s)

    for trip_id, rows in stop_times_by_trip.items():
        line_id = line_of_trip.get(trip_id)
        if not line_id:
            continue

        rows.sort(key=lambda r: int(r[st_idx["stop_sequence"]]))

        for a, b in zip(rows, rows[1:]):
            from_place = place_of_stop.get(a[st_idx["stop_id"]])
            to_place = place_of_stop.get(b[st_idx["stop_id"]])

            if not from_place or not to_place or from_place == to_place:
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
                from_stop = stations[from_place]
                to_stop = stations[to_place]
                distance_m = haversine_m(
                    from_stop["latitude"], from_stop["longitude"],
                    to_stop["latitude"], to_stop["longitude"],
                )

            if distance_m <= 0:
                continue  # same fix as the zero-distance bug, applied at the source

            key = (from_place, to_place, line_id)
            candidate = (round(distance_m), round(duration_s))

            if key not in best or candidate[1] < best[key][1]:
                best[key] = candidate

    for (from_place, to_place, line_id), (distance_m, duration_s) in best.items():
        connections[(from_place, to_place, line_id)] = {
            "from": from_place,
            "to": to_place,
            "line": line_id,
            "mode": mode,
            "distance_m": distance_m,
            "duration_s": duration_s,
        }
        for place_id in (from_place, to_place):
            if line_id not in stations[place_id]["lines"]:
                stations[place_id]["lines"].append(line_id)


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

    process_feed(
        GTFS_METRO, "metro",
        lambda route_id: METRO_LINE_FOR_ROUTE.get(route_id),
        stations, lines, connections,
    )

    write_json(OUTPUT / "stations.json", sorted(stations.values(), key=lambda s: s["id"]))
    write_json(OUTPUT / "lines.json", sorted(lines.values(), key=lambda l: l["id"]))
    write_json(
        OUTPUT / "connections.json",
        sorted(connections.values(), key=lambda c: (c["from"], c["to"], c["line"])),
    )

    print(f"metro: {len(stations)} stations, {len(lines)} lines, {len(connections)} connections")


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
