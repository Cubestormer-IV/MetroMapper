"""One-time fix: Majlis Park became a real Pink/Magenta interchange only
with the extensions added this session (it wasn't one when
split_interchange_platforms.py originally ran, so it was missed). Applies
the same platform-split treatment to just this one station: splits it
into 173_pink/173_magenta platform children under a parent stop, repoints
stop_times, and adds a transfers.txt entry with the same ~5min + noise
placeholder used everywhere else.

Not idempotent -- not meant to be re-run.
"""
import csv
import random
from pathlib import Path

from convert_to_canonical import read_rows, METRO_LINE_FOR_ROUTE

GTFS = Path(__file__).resolve().parent.parent / "app/src/main/assets/data/gtfs/metro"
STOP_ID = "173"
random.seed(173)


def write_rows(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def append_rows(path, rows):
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)


stops_idx, stops_rows = read_rows(GTFS / "stops.txt")
trips_idx, trips_rows = read_rows(GTFS / "trips.txt")
st_idx, st_rows = read_rows(GTFS / "stop_times.txt")

line_of_trip = {}
for row in trips_rows:
    line = METRO_LINE_FOR_ROUTE.get(row[trips_idx["route_id"]])
    if line:
        line_of_trip[row[trips_idx["trip_id"]]] = line

lines_at_stop = set()
for row in st_rows:
    if row[st_idx["stop_id"]] == STOP_ID:
        line = line_of_trip.get(row[st_idx["trip_id"]])
        if line:
            lines_at_stop.add(line)

print(f"Majlis Park serves: {sorted(lines_at_stop)}")
assert len(lines_at_stop) > 1, "expected Majlis Park to be a real interchange by now"

child_id_of = {line: f"{STOP_ID}_{line}" for line in lines_at_stop}

new_stop_rows = []
for row in stops_rows:
    if row[stops_idx["stop_id"]] == STOP_ID:
        new_stop_rows.append(list(row[:len(stops_idx)]) + ["1", ""])  # parent
        for line in sorted(lines_at_stop):
            child_row = list(row[:len(stops_idx)])
            child_row[stops_idx["stop_id"]] = child_id_of[line]
            child_row += ["0", STOP_ID]
            new_stop_rows.append(child_row)
    else:
        new_stop_rows.append(row)

write_rows(GTFS / "stops.txt", list(stops_idx.keys()), new_stop_rows)
print(f"stops.txt: added {len(lines_at_stop)} platform rows for Majlis Park")

new_st_rows = []
repointed = 0
for row in st_rows:
    if row[st_idx["stop_id"]] == STOP_ID:
        line = line_of_trip.get(row[st_idx["trip_id"]])
        child_id = child_id_of.get(line)
        if child_id:
            row = list(row)
            row[st_idx["stop_id"]] = child_id
            repointed += 1
    new_st_rows.append(row)

write_rows(GTFS / "stop_times.txt", list(st_idx.keys()), new_st_rows)
print(f"stop_times.txt: repointed {repointed} rows")

seconds = max(60, round(random.gauss(300, 60)))
lines_sorted = sorted(lines_at_stop)
transfer_rows = []
for i, line_a in enumerate(lines_sorted):
    for line_b in lines_sorted[i + 1:]:
        a, b = child_id_of[line_a], child_id_of[line_b]
        transfer_rows.append([a, b, "2", seconds])
        transfer_rows.append([b, a, "2", seconds])

append_rows(GTFS / "transfers.txt", transfer_rows)
print(f"transfers.txt: added {len(transfer_rows)} rows ({seconds}s)")
