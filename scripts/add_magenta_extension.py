"""One-time fix: adds the Majlis Park <-> Deepali Chowk Magenta Line
stretch (Bhalswa, Haiderpur Badli Mor, Haiderpur Village, Uttar Pitampura
- Prashant Vihar, Madhuban Chowk, Deepali Chowk) to the GTFS data.

Deliberately NOT connected to the rest of Magenta (Botanical Garden <->
Krishna Park Extension) -- the Krishna Park Extension <-> Deepali Chowk
link is still under Phase 4 construction, not open, so a rider genuinely
cannot travel between the two stretches today. No stop_id is shared with
the other stretch (Majlis Park is only otherwise linked to Pink Line in
our data), so the routing graph stays correctly split into two
components without any extra work.

Coordinates from OpenStreetMap (~/Downloads/delhi_metro_lines.geojson),
order confirmed against Wikipedia's station list. No real schedule exists
for this stretch either, so times are estimated the same way as the Pink
Line extension (haversine distance / ~33 km/h + 20s dwell), a single
representative round trip rather than a full day's schedule.

Not idempotent -- not meant to be re-run against its own output.
"""
import csv
import math

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
AVG_SPEED_MPS = 33 * 1000 / 3600
DWELL_S = 20
START_TIME_S = 6 * 3600 + 10 * 60  # 06:10:00

NEW_STATIONS = [
    # (stop_id, name, lat, lon) -- order is Majlis-Park-ward to Deepali-Chowk-ward
    ("529", "Bhalswa", 28.736919, 77.168071),
    ("530", "Haiderpur Badli Mor", 28.729820, 77.148880),
    ("531", "Haiderpur Village", 28.724881, 77.142437),
    ("532", "Uttar Pitampura - Prashant Vihar", 28.713082, 77.138672),
    ("533", "Madhuban Chowk", 28.703568, 77.130072),
    ("534", "Deepali Chowk", 28.698094, 77.118277),
]

MAJLIS_PARK = ("173", "Majlis Park", 28.724157, 77.182068)

ROUTE_ID = "Delhi8"
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


with open(f"{FEED_DIR}/stops.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for stop_id, name, lat, lon in NEW_STATIONS:
        writer.writerow([stop_id, "", name, "", lat, lon, "0", ""])

print(f"Added {len(NEW_STATIONS)} stops to stops.txt")

forward = [MAJLIS_PARK] + NEW_STATIONS
backward = list(reversed(forward))

trip_ids = {"forward": "magenta_ext_fwd_1", "backward": "magenta_ext_rev_1"}

with open(f"{FEED_DIR}/trips.txt", "a", newline="") as f:
    writer = csv.writer(f)
    for direction, trip_id in trip_ids.items():
        writer.writerow([ROUTE_ID, SERVICE_ID, trip_id, "", "", "", "", "", "0", "0"])

print(f"Added trips: {list(trip_ids.values())}")


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
