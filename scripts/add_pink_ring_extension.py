"""One-time fix: adds the Majlis Park <-> Maujpur-Babarpur direct link
(Yamuna Vihar, Bhajanpura, Khajuri Khas, Soorghat, Sonia Vihar, Jagatpur
Village, Jharoda Majra, Burari) to the Pink Line GTFS data. This stretch
opened 2026-03-08 and closed Pink Line into a ring; it was entirely
missing from our source feed. Coordinates come from OpenStreetMap
(~/Downloads/delhi_metro_lines.geojson), station order/names confirmed
against real-world knowledge and the Wikipedia station list.

No real schedule exists for this stretch in our source feed, so times
are estimated (haversine distance / ~33 km/h cruising speed + 20s dwell
per stop) rather than real GTFS data -- same kind of placeholder as the
interchange transfer times, clearly a single representative round trip
rather than a full day's schedule.

Not idempotent -- not meant to be re-run against its own output.
"""
import csv
import math

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
AVG_SPEED_MPS = 33 * 1000 / 3600
DWELL_S = 20
START_TIME_S = 6 * 3600 + 10 * 60  # 06:10:00

NEW_STATIONS = [
    # (stop_id, name, lat, lon) -- order is Maujpur-Babarpur-ward to Majlis-Park-ward
    ("521", "Yamuna Vihar", 28.702379, 77.277306),
    ("522", "Bhajanpura", 28.703598, 77.262645),
    ("523", "Khajuri Khas", 28.705184, 77.254473),
    ("524", "Soorghat", 28.708695, 77.242503),
    ("525", "Sonia Vihar", 28.710225, 77.227471),
    ("526", "Jagatpur Village", 28.721150, 77.223935),
    ("527", "Jharoda Majra", 28.724883, 77.213678),
    ("528", "Burari", 28.729829, 77.199574),
]

MAUJPUR_BABARPUR = ("215", "Maujpur - Babarpur", 28.692057, 77.280922)
MAJLIS_PARK = ("173", "Majlis Park", 28.724157, 77.182068)

ROUTE_ID = "Delhi7"
SERVICE_ID = "weekday"


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def fmt_time(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --- 1. append new stops ---------------------------------------------------
with open(f"{FEED_DIR}/stops.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for stop_id, name, lat, lon in NEW_STATIONS:
        writer.writerow([stop_id, "", name, "", lat, lon, "0", ""])

print(f"Added {len(NEW_STATIONS)} stops to stops.txt")

# --- 2. build the two directions of stops (with coords) --------------------
forward = [MAUJPUR_BABARPUR] + NEW_STATIONS + [MAJLIS_PARK]
backward = list(reversed(forward))

# --- 3. append trips -------------------------------------------------------
trip_ids = {"forward": "pink_ext_fwd_1", "backward": "pink_ext_rev_1"}

with open(f"{FEED_DIR}/trips.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for direction, trip_id in trip_ids.items():
        writer.writerow([ROUTE_ID, SERVICE_ID, trip_id, "", "", "", "", "", "0", "0"])

print(f"Added trips: {list(trip_ids.values())}")

# --- 4. append stop_times, with estimated cumulative timing ---------------
def write_stop_times(writer, trip_id, stops_seq):
    t = START_TIME_S
    cumulative_dist = 0.0
    prev = None
    for seq, (stop_id, name, lat, lon) in enumerate(stops_seq, start=1):
        if prev is not None:
            dist = haversine_m(prev[2], prev[3], lat, lon)
            cumulative_dist += dist
            t += dist / AVG_SPEED_MPS
        arrival = fmt_time(t)
        t += DWELL_S
        departure = fmt_time(t)
        writer.writerow([trip_id, arrival, departure, stop_id, seq, "", "0", "0", f"{cumulative_dist:.1f}", "1", "", ""])
        prev = (stop_id, name, lat, lon)


with open(f"{FEED_DIR}/stop_times.txt", "a", newline="") as f:
    writer = csv.writer(f)
    write_stop_times(writer, trip_ids["forward"], forward)
    write_stop_times(writer, trip_ids["backward"], backward)

print("Added stop_times for both directions")
