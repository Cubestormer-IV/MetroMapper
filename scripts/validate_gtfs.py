"""Scans a GTFS feed for specific corruption patterns found by hand in the
metro data (duplicated stop coordinates, duplicated/non-increasing
shape_dist_traveled within a trip). Read-only — prints findings, changes
nothing.

Usage: python3 scripts/validate_gtfs.py [feed_dir]
Defaults to app/src/main/assets/data/gtfs/metro.
"""
import csv
import sys
from collections import defaultdict

FEED_DIR = sys.argv[1] if len(sys.argv) > 1 else "app/src/main/assets/data/gtfs/metro"


def check_duplicate_coordinates():
    with open(f"{FEED_DIR}/stops.txt", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        id_idx = header.index("stop_id")
        name_idx = header.index("stop_name")
        lat_idx = header.index("stop_lat")
        lon_idx = header.index("stop_lon")

        by_coord = defaultdict(list)
        for row in reader:
            coord = (row[lat_idx], row[lon_idx])
            by_coord[coord].append((row[id_idx], row[name_idx]))

    print("=== Stops sharing identical coordinates ===")
    found = 0
    for coord, stops in by_coord.items():
        if len(stops) > 1:
            found += 1
            names = ", ".join(f"{sid} ({name})" for sid, name in stops)
            print(f"  {coord}: {names}")
    if not found:
        print("  none found")


def check_shape_dist_traveled():
    with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        trip_idx = header.index("trip_id")
        stop_idx = header.index("stop_id")
        seq_idx = header.index("stop_sequence")
        dist_idx = header.index("shape_dist_traveled")

        rows = [
            (row[trip_idx], int(row[seq_idx]), row[stop_idx], float(row[dist_idx]))
            for row in reader
            if row[dist_idx]
        ]

    rows.sort(key=lambda r: (r[0], r[1]))

    print("\n=== Non-increasing shape_dist_traveled within a trip ===")
    bad_pairs = defaultdict(set)
    prev_trip = None
    prev_stop = None
    prev_dist = None
    for trip_id, seq, stop_id, dist in rows:
        if trip_id == prev_trip and dist <= prev_dist:
            bad_pairs[(prev_stop, stop_id)].add(trip_id)
        prev_trip, prev_stop, prev_dist = trip_id, stop_id, dist

    if not bad_pairs:
        print("  none found")
        return

    for (from_stop, to_stop), trips in bad_pairs.items():
        sample = next(iter(trips))
        print(f"  {from_stop} -> {to_stop}  ({len(trips)} trip(s), e.g. trip {sample})")


if __name__ == "__main__":
    check_duplicate_coordinates()
    check_shape_dist_traveled()
