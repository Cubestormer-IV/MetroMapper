"""One-time fix: stop 38 ("Haiderpur Badli Mor" in the original raw feed,
already wired into real Yellow Line schedule data) and stop 530 (the
same real station, added separately this session for the Magenta
extension, with the correct OSM-sourced coordinate) are duplicates of one
real Yellow/Magenta interchange -- same pattern as Sikanderpur's 148/68_rapid
duplicate found earlier. Stop 38's coordinate was wrong by 1.26km;
530's is correct (confirmed against OSM directly).

Merges them: splits 530 into a proper interchange (530_yellow,
530_magenta), repoints every stop_times row from 38 -> 530_yellow and
from 530 -> 530_magenta, removes 38 entirely, and adds a transfer entry
with the same placeholder style used for every other interchange.

Not idempotent -- not meant to be re-run.
"""
import csv
import random

FEED_DIR = "app/src/main/assets/data/gtfs/metro"
random.seed(530)

with open(f"{FEED_DIR}/stops.txt", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

i_id = header.index("stop_id")
i_loc = header.index("location_type")
i_parent = header.index("parent_station")

parent_row = next(row for row in rows if row[i_id] == "530")
new_rows = []
for row in rows:
    if row[i_id] == "38":
        continue  # drop the duplicate entirely
    if row[i_id] == "530":
        parent = list(row)
        parent[i_loc] = "1"
        new_rows.append(parent)
        for line in ("yellow", "magenta"):
            child = list(row)
            child[i_id] = f"530_{line}"
            child[i_loc] = "0"
            child[i_parent] = "530"
            new_rows.append(child)
    else:
        new_rows.append(row)

with open(f"{FEED_DIR}/stops.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(new_rows)

print("stops.txt: merged 38 into 530, split into 530_yellow/530_magenta")

with open(f"{FEED_DIR}/stop_times.txt", newline="") as f:
    reader = csv.reader(f)
    st_header = next(reader)
    st_rows = list(reader)

i_sid = st_header.index("stop_id")
repointed_yellow = 0
repointed_magenta = 0
for row in st_rows:
    if row[i_sid] == "38":
        row[i_sid] = "530_yellow"
        repointed_yellow += 1
    elif row[i_sid] == "530":
        row[i_sid] = "530_magenta"
        repointed_magenta += 1

with open(f"{FEED_DIR}/stop_times.txt", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(st_header)
    writer.writerows(st_rows)

print(f"stop_times.txt: repointed {repointed_yellow} rows (38->530_yellow), "
      f"{repointed_magenta} rows (530->530_magenta)")

seconds = max(60, round(random.gauss(300, 60)))
with open(f"{FEED_DIR}/transfers.txt", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["530_yellow", "530_magenta", "2", seconds])
    writer.writerow(["530_magenta", "530_yellow", "2", seconds])

print(f"transfers.txt: added 530_yellow <-> 530_magenta ({seconds}s)")
