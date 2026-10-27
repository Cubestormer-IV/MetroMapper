"""One-time fix: stop_times.txt has corrupted shape_dist_traveled for the
Bhikaji Cama Place (204) <-> Sarojini Nagar (205) pair -- identical or
near-identical values regardless of direction, instead of the real
~1.36km gap. This silently dropped the bhikaji_cama_place -> sarojini_nagar
edge entirely (zero distance gets filtered out) and gave the reverse edge
a bogus ~1m distance.

Corrects every affected trip properly: for the stop that comes second
(either 204 or 205, depending on direction), sets its shape_dist_traveled
to the real along-track distance from the real OSM Pink ring geometry
(1359.4m, computed separately), then shifts every later stop in that same
trip by the same delta -- so the rest of each trip's cumulative distances
stay consistent instead of only patching the one broken gap.

Not idempotent -- not meant to be re-run against its own output.
"""
import csv

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
REAL_DISTANCE_M = 1359.4


def main():
    with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    i_tid = header.index("trip_id")
    i_sid = header.index("stop_id")
    i_seq = header.index("stop_sequence")
    i_dist = header.index("shape_dist_traveled")

    by_trip = {}
    for i, row in enumerate(rows):
        by_trip.setdefault(row[i_tid], []).append(i)

    fixed_trips = 0
    shifted_rows = 0

    for trip_id, indices in by_trip.items():
        indices.sort(key=lambda i: int(rows[i][i_seq]))
        stop_at = [(i, rows[i][i_sid]) for i in indices]
        ids = [sid for _, sid in stop_at]

        if "204" not in ids or "205" not in ids:
            continue

        pos204, pos205 = ids.index("204"), ids.index("205")
        if abs(pos204 - pos205) != 1:
            continue  # not adjacent in this trip, leave alone

        first_pos, second_pos = min(pos204, pos205), max(pos204, pos205)
        first_i = stop_at[first_pos][0]
        second_i = stop_at[second_pos][0]

        first_dist = float(rows[first_i][i_dist])
        old_second_dist = float(rows[second_i][i_dist])
        new_second_dist = first_dist + REAL_DISTANCE_M
        delta = new_second_dist - old_second_dist

        if abs(delta) < 0.01:
            continue  # already correct, don't touch

        for pos in range(second_pos, len(stop_at)):
            i = stop_at[pos][0]
            old = float(rows[i][i_dist])
            rows[i][i_dist] = f"{old + delta:.1f}"
            shifted_rows += 1

        fixed_trips += 1

    with open(f"{FEED_DIR}/stop_times.txt", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Fixed {fixed_trips} trips, shifted {shifted_rows} downstream rows")


if __name__ == "__main__":
    main()
