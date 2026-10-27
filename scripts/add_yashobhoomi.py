"""One-time fix: adds Yashobhoomi Dwarka Sector 25, the real Airport
Express terminus extension beyond Dwarka Sector 21 (opened 2023-09-17,
~1.9km, entirely missing from our feed). Extends every existing
DelhiAirport trip properly -- appends it after Dwarka Sector 21 for
outbound trips, prepends it before for inbound trips (shifting every
other stop's shape_dist_traveled by the same delta) -- rather than
adding one new sample trip alongside the real ones.

Speed estimate (~60 km/h) comes from this line's own real segments
(computed from existing stop_times), not the generic ~33 km/h regular
metro assumption used for Pink/Magenta's extensions, since Airport
Express runs significantly faster.

Not idempotent -- not meant to be re-run.
"""
import csv
import math

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
NEW_STOP_ID = "121_orange_ext"  # temp id for the new raw stop before any splitting
STOP_CODE = "IICC"
NAME = "Yashobhoomi Dwarka Sector - 25"
LAT, LON = 28.5508323, 77.0453073
DWARKA_21_LAT, DWARKA_21_LON = None, None  # filled in from stops.txt
AVG_SPEED_MPS = 60 * 1000 / 3600
DWELL_S = 20


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def gtfs_time_to_seconds(value):
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def seconds_to_gtfs_time(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

i_id = header.index("stop_id")
i_code = header.index("stop_code")
i_name = header.index("stop_name")
i_lat = header.index("stop_lat")
i_lon = header.index("stop_lon")

dwarka_row = next(row for row in rows if row[i_id] == "121_orange")
DWARKA_21_LAT, DWARKA_21_LON = float(dwarka_row[i_lat]), float(dwarka_row[i_lon])
dist_m = haversine_m(DWARKA_21_LAT, DWARKA_21_LON, LAT, LON)
travel_s = dist_m / AVG_SPEED_MPS
print(f"Dwarka Sector 21 -> Yashobhoomi: {dist_m:.0f}m, ~{travel_s:.0f}s at {AVG_SPEED_MPS*3.6:.0f} km/h")

new_row = [""] * len(header)
new_row[i_id] = NEW_STOP_ID
new_row[i_code] = STOP_CODE
new_row[i_name] = NAME
new_row[i_lat] = str(LAT)
new_row[i_lon] = str(LON)
loc_idx = header.index("location_type")
new_row[loc_idx] = "0"
rows.append(new_row)

with open(f"{FEED_DIR}/stops.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print("Added Yashobhoomi stop to stops.txt")

with open(f"{FEED_DIR}/trips.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    trip_rows = list(reader)

i_rid, i_tid = header.index("route_id"), header.index("trip_id")
airport_trips = {row[i_tid] for row in trip_rows if row[i_rid] == "DelhiAirport"}
print(f"{len(airport_trips)} DelhiAirport trips to extend")

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

by_trip = {}
for i, row in enumerate(st_rows):
    if row[i_tid2] in airport_trips:
        by_trip.setdefault(row[i_tid2], []).append(i)

new_rows = []
outbound_count = 0
inbound_count = 0

for trip_id, indices in by_trip.items():
    indices.sort(key=lambda i: int(st_rows[i][i_seq2]))
    first_i, last_i = indices[0], indices[-1]

    if st_rows[last_i][i_sid2] == "121_orange":
        # outbound: append Yashobhoomi after Dwarka Sector 21
        last = st_rows[last_i]
        t = gtfs_time_to_seconds(last[i_dep2]) + travel_s
        base_dist = float(last[i_dist2])
        row = [""] * len(st_header)
        row[i_tid2] = trip_id
        row[i_arr2] = seconds_to_gtfs_time(t)
        row[i_dep2] = seconds_to_gtfs_time(t + DWELL_S)
        row[i_sid2] = NEW_STOP_ID
        row[i_seq2] = str(int(last[i_seq2]) + 1)
        row[i_dist2] = f"{base_dist + dist_m:.1f}"
        st_header_pickup = st_header.index("pickup_type")
        st_header_dropoff = st_header.index("drop_off_type")
        row[st_header_pickup] = "0"
        row[st_header_dropoff] = "0"
        new_rows.append(row)
        outbound_count += 1

    elif st_rows[first_i][i_sid2] == "121_orange":
        # inbound: prepend Yashobhoomi before Dwarka Sector 21, shift everything
        first = st_rows[first_i]
        t = gtfs_time_to_seconds(first[i_arr2]) - DWELL_S - travel_s
        row = [""] * len(st_header)
        row[i_tid2] = trip_id
        row[i_arr2] = seconds_to_gtfs_time(t)
        row[i_dep2] = seconds_to_gtfs_time(t + DWELL_S)
        row[i_sid2] = NEW_STOP_ID
        row[i_seq2] = str(int(first[i_seq2]) - 1)
        row[i_dist2] = "0.0"
        st_header_pickup = st_header.index("pickup_type")
        st_header_dropoff = st_header.index("drop_off_type")
        row[st_header_pickup] = "0"
        row[st_header_dropoff] = "0"
        new_rows.append(row)

        for i in indices:
            st_rows[i][i_dist2] = f"{float(st_rows[i][i_dist2]) + dist_m:.1f}"
        inbound_count += 1

    else:
        raise ValueError(f"trip {trip_id} doesn't start or end at Dwarka Sector 21 as expected")

st_rows.extend(new_rows)

with open(f"{FEED_DIR}/stop_times.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(st_header)
    writer.writerows(st_rows)

print(f"Extended {outbound_count} outbound and {inbound_count} inbound trips")
