"""Finds stations where a line genuinely branches (more than 2 distinct
neighboring stops across all trips) rather than running as a simple
there-and-back line. These are candidates for the same split-node +
timed Walk-edge treatment already applied to interchanges, since reaching
one branch from the other requires reversing effective direction.

Read-only. Usage: python3 scripts/find_branch_junctions.py [feed_dir]
"""
import csv
import sys
from collections import defaultdict

FEED_DIR = sys.argv[1] if len(sys.argv) > 1 else "app/src/main/assets/data/gtfs/metro"

rows_by_trip = defaultdict(list)
with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    trip_idx = header.index("trip_id")
    stop_idx = header.index("stop_id")
    seq_idx = header.index("stop_sequence")
    for row in reader:
        rows_by_trip[row[trip_idx]].append((int(row[seq_idx]), row[stop_idx]))

names = {}
with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    id_idx = header.index("stop_id")
    name_idx = header.index("stop_name")
    for row in reader:
        names[row[id_idx]] = row[name_idx]

neighbors = defaultdict(set)
for trip_id, stops in rows_by_trip.items():
    stops.sort()
    for i, (seq, stop_id) in enumerate(stops):
        if i > 0:
            neighbors[stop_id].add(stops[i - 1][1])
        if i < len(stops) - 1:
            neighbors[stop_id].add(stops[i + 1][1])

print("=== Stations with more than 2 distinct neighbors (branch candidates) ===")
for stop_id, ns in sorted(neighbors.items(), key=lambda kv: -len(kv[1])):
    if len(ns) > 2:
        neighbor_names = ", ".join(f"{names.get(n, n)} ({n})" for n in ns)
        print(f"  {names.get(stop_id, stop_id)} ({stop_id}): {len(ns)} neighbors -> {neighbor_names}")
