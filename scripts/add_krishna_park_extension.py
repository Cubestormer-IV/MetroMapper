"""One-time fix: adds Krishna Park Extension, the real current Magenta
Line trunk terminus beyond Janak Puri West (opened 2025-01-05, ~2.8km,
one station, entirely missing from our feed -- our data still ends at
the old pre-2025 terminus). Extends every real existing Magenta trunk
trip that touches Janak Puri West's platform (108_magenta) properly,
the same way Yashobhoomi was added to Airport Express -- not a new
synthetic trip alongside the real ones.

Speed estimate (~37 km/h) comes from this line's own real segments
(computed from existing stop_times near Janak Puri West), not a generic
assumption.

Deliberately skips the already-added Majlis Park <-> Deepali Chowk
extension trips, which don't touch Janak Puri West at all and must stay
disconnected from this trunk (same real-world construction gap as
before).

Not idempotent -- not meant to be re-run.
"""
import csv
import math

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
NEW_STOP_ID = "108_magenta_ext"
STOP_CODE = "KPEN"
NAME = "Krishna Park Extension"
LAT, LON = 28.6477917, 77.0843425
DIST_M = 2800
AVG_SPEED_MPS = 37 * 1000 / 3600
TRAVEL_S = DIST_M / AVG_SPEED_MPS
DWELL_S = 20


def gtfs_time_to_seconds(value):
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def seconds_to_gtfs_time(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


print(f"Janak Puri West -> Krishna Park Extension: {DIST_M}m, ~{TRAVEL_S:.0f}s at {AVG_SPEED_MPS*3.6:.0f} km/h")

with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

i_id = header.index("stop_id")
i_code = header.index("stop_code")
i_name = header.index("stop_name")
i_lat = header.index("stop_lat")
i_lon = header.index("stop_lon")
i_loc = header.index("location_type")

new_row = [""] * len(header)
new_row[i_id] = NEW_STOP_ID
new_row[i_code] = STOP_CODE
new_row[i_name] = NAME
new_row[i_lat] = str(LAT)
new_row[i_lon] = str(LON)
new_row[i_loc] = "0"
rows.append(new_row)

with open(f"{FEED_DIR}/stops.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print("Added Krishna Park Extension stop to stops.txt")

with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    trip_rows = list(reader)

i_rid, i_tid = header.index("route_id"), header.index("trip_id")
magenta_trips = {row[i_tid] for row in trip_rows if row[i_rid] == "Delhi8"}

with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
    reader = csv.reader(f)
    st_header = next(reader)
    st_rows = list(reader)

i_tid2 = st_header.index("trip_id")
i_sid2 = st_header.index("stop_id")
i_seq2 = st_header.index("stop_sequence")
i_arr2 = st_header.index("arrival_time")
i_dep2 = st_header.index("departure_time")
i_dist2 = st_header.index("shape_dist_traveled")
i_pickup = st_header.index("pickup_type")
i_dropoff = st_header.index("drop_off_type")

by_trip = {}
for i, row in enumerate(st_rows):
    if row[i_tid2] in magenta_trips:
        by_trip.setdefault(row[i_tid2], []).append(i)

new_rows = []
outbound_count = 0
inbound_count = 0
skipped = 0

for trip_id, indices in by_trip.items():
    indices.sort(key=lambda i: int(st_rows[i][i_seq2]))
    stop_ids_here = [st_rows[i][i_sid2] for i in indices]
    if "108_magenta" not in stop_ids_here:
        skipped += 1
        continue  # the disconnected Majlis Park <-> Deepali Chowk extension trips

    first_i, last_i = indices[0], indices[-1]

    if st_rows[last_i][i_sid2] == "108_magenta":
        last = st_rows[last_i]
        t = gtfs_time_to_seconds(last[i_dep2]) + TRAVEL_S
        base_dist = float(last[i_dist2])
        row = [""] * len(st_header)
        row[i_tid2] = trip_id
        row[i_arr2] = seconds_to_gtfs_time(t)
        row[i_dep2] = seconds_to_gtfs_time(t + DWELL_S)
        row[i_sid2] = NEW_STOP_ID
        row[i_seq2] = str(int(last[i_seq2]) + 1)
        row[i_dist2] = f"{base_dist + DIST_M:.1f}"
        row[i_pickup] = "0"
        row[i_dropoff] = "0"
        new_rows.append(row)
        outbound_count += 1

    elif st_rows[first_i][i_sid2] == "108_magenta":
        first = st_rows[first_i]
        t = gtfs_time_to_seconds(first[i_arr2]) - DWELL_S - TRAVEL_S
        row = [""] * len(st_header)
        row[i_tid2] = trip_id
        row[i_arr2] = seconds_to_gtfs_time(t)
        row[i_dep2] = seconds_to_gtfs_time(t + DWELL_S)
        row[i_sid2] = NEW_STOP_ID
        row[i_seq2] = str(int(first[i_seq2]) - 1)
        row[i_dist2] = "0.0"
        row[i_pickup] = "0"
        row[i_dropoff] = "0"
        new_rows.append(row)

        for i in indices:
            st_rows[i][i_dist2] = f"{float(st_rows[i][i_dist2]) + DIST_M:.1f}"
        inbound_count += 1

    else:
        raise ValueError(f"trip {trip_id} has 108_magenta but not as first or last stop")

st_rows.extend(new_rows)

with open(f"{FEED_DIR}/stop_times.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(st_header)
    writer.writerows(st_rows)

print(f"Extended {outbound_count} outbound and {inbound_count} inbound trips; "
      f"skipped {skipped} (the disconnected Majlis Park<->Deepali Chowk extension)")
