"""
One-time migration: upgrades app/src/main/assets/data/gtfs/metro/ from DMRC's
flat "one stop_id per station" feed into standard GTFS platform modeling —
one stop_id per (station, line), linked to a parent station via
location_type/parent_station, exactly as the GTFS spec defines them.

Also writes transfers.txt connecting the new platform ids at every
interchange, with a placeholder min_transfer_time (5 min + noise — replace
with real values by hand once known).

Run once against the raw-ish feed. Running it again against its own output
would mis-detect the already-split rows as new interchanges — not guarded
against, since this isn't meant to be repeatable like convert_to_canonical.py.
"""

import csv
import random
from pathlib import Path

from convert_to_canonical import read_rows, METRO_LINE_FOR_ROUTE

GTFS = Path(__file__).resolve().parent.parent / "app/src/main/assets/data/gtfs/metro"

random.seed(7)  # fixed, so this one-time run is reproducible; edit transfers.txt by hand afterward


def write_rows(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    stops_idx, stops_rows = read_rows(GTFS / "stops.txt")
    trips_idx, trips_rows = read_rows(GTFS / "trips.txt")
    st_idx, st_rows = read_rows(GTFS / "stop_times.txt")

    line_of_trip = {}
    for row in trips_rows:
        line = METRO_LINE_FOR_ROUTE.get(row[trips_idx["route_id"]])
        if line:
            line_of_trip[row[trips_idx["trip_id"]]] = line

    # which lines serve each raw stop_id
    lines_of_stop = {}
    for row in st_rows:
        line = line_of_trip.get(row[st_idx["trip_id"]])
        if line:
            lines_of_stop.setdefault(row[st_idx["stop_id"]], set()).add(line)

    interchanges = {sid: lines for sid, lines in lines_of_stop.items() if len(lines) > 1}
    print(f"found {len(interchanges)} interchange stops")

    # --- stops.txt: add location_type/parent_station, add platform children ---

    new_header = stops_rows and list(stops_idx.keys()) or []
    new_header = [h for h in stops_idx] + ["location_type", "parent_station"]

    new_stop_rows = []
    child_id_of = {}  # (stop_id, line) -> new platform id

    for row in stops_rows:
        stop_id = row[stops_idx["stop_id"]]
        if stop_id in interchanges:
            parent_row = list(row) + ["1", ""]  # this becomes the parent station
            new_stop_rows.append(parent_row)

            for line in sorted(interchanges[stop_id]):
                child_id = f"{stop_id}_{line}"
                child_id_of[(stop_id, line)] = child_id
                child_row = list(row)
                child_row[stops_idx["stop_id"]] = child_id
                child_row += ["0", stop_id]
                new_stop_rows.append(child_row)
        else:
            new_stop_rows.append(list(row) + ["0", ""])

    write_rows(GTFS / "stops.txt", new_header, new_stop_rows)
    print(f"stops.txt: {len(stops_rows)} -> {len(new_stop_rows)} rows "
          f"(+{len(new_stop_rows) - len(stops_rows)} platforms)")

    # --- stop_times.txt: repoint interchange rows at the right platform ---

    new_st_rows = []
    repointed = 0

    for row in st_rows:
        stop_id = row[st_idx["stop_id"]]
        if stop_id in interchanges:
            line = line_of_trip.get(row[st_idx["trip_id"]])
            child_id = child_id_of.get((stop_id, line))
            if child_id:
                row = list(row)
                row[st_idx["stop_id"]] = child_id
                repointed += 1
        new_st_rows.append(row)

    write_rows(GTFS / "stop_times.txt", list(st_idx.keys()), new_st_rows)
    print(f"stop_times.txt: repointed {repointed} rows")

    # --- transfers.txt: one noisy ~5 min placeholder per station, every line pair ---

    transfer_header = ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"]
    transfer_rows = []

    for stop_id, lines in interchanges.items():
        seconds = max(60, round(random.gauss(300, 60)))
        lines = sorted(lines)
        for i, line_a in enumerate(lines):
            for line_b in lines[i + 1:]:
                a, b = child_id_of[(stop_id, line_a)], child_id_of[(stop_id, line_b)]
                transfer_rows.append([a, b, "2", seconds])
                transfer_rows.append([b, a, "2", seconds])

    write_rows(GTFS / "transfers.txt", transfer_header, transfer_rows)
    print(f"transfers.txt: {len(transfer_rows)} rows")


if __name__ == "__main__":
    main()
