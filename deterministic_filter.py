#!/usr/bin/env python3
"""
stream_flag_ais.py

Stream-process an AIS CSV, flag each row by deterministic rules,
and write out a new CSV—without ever holding the whole dataset in memory.
"""

import csv
import math
from datetime import datetime, timedelta
from tqdm import tqdm

# ─── thresholds ───────────────────────────────────────────────────────────────
SOG_MAX = 30.0                        # knots
OFFLINE_THRESHOLD = timedelta(hours=1)
ALLOW_START = 23.5                    # 23:30 as decimal hour
ALLOW_END   = 0.5                     # 00:30 as decimal hour
FREQ_THRESHOLD = timedelta(minutes=10)
HEADING_JUMP = 45.0                   # degrees
DISTANCE_KM = 10.0                    # km

# ─── utils ────────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    """Return haversine distance (km) between two points."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def in_midnight_allow(hour_min):
    """True if time (in decimal hours) is between 23:30–00:30."""
    return (hour_min >= ALLOW_START) or (hour_min <= ALLOW_END)

# ─── main ─────────────────────────────────────────────────────────────────────
def stream_flag(input_path, output_path):
    prev = {}  # MMSI -> (timestamp, lat, lon, cog)

    with open(input_path, newline='') as fin, \
         open(output_path, 'w', newline='') as fout:

        reader = csv.DictReader(fin)
        flags = ["flag_speed", "flag_offline", "flag_low_freq",
                 "flag_heading", "flag_distance", "flag_any"]
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames + flags)
        writer.writeheader()

        for row in tqdm(reader, desc="Processing rows"):
            m = row["MMSI"]
            # parse current
            t = datetime.fromisoformat(row["BaseDateTime"])
            lat = float(row["LAT"])
            lon = float(row["LON"])
            sog = float(row["SOG"]) if row["SOG"] else 0.0
            cog = float(row["COG"]) if row["COG"] else 0.0

            # rule 1: speed
            f_speed = sog > SOG_MAX

            # default others
            f_off = f_freq = f_head = f_dist = False

            if m in prev:
                t0, lat0, lon0, cog0 = prev[m]
                Δt = t - t0

                # rule 2: offline gap outside midnight window
                h0 = t0.hour + t0.minute/60
                long_gap = Δt > OFFLINE_THRESHOLD
                f_off = long_gap and not in_midnight_allow(h0)

                # rule 3: low frequency
                f_freq = Δt > FREQ_THRESHOLD

                # rule 4: heading jump
                f_head = abs(cog - cog0) > HEADING_JUMP

                # rule 5: distance jump
                dist = haversine(lat0, lon0, lat, lon)
                f_dist = dist > DISTANCE_KM

            # aggregate
            f_any = any([f_speed, f_off, f_freq, f_head, f_dist])

            # write flags into row
            row.update({
                "flag_speed":    str(int(f_speed)),
                "flag_offline":  str(int(f_off)),
                "flag_low_freq": str(int(f_freq)),
                "flag_heading":  str(int(f_head)),
                "flag_distance": str(int(f_dist)),
                "flag_any":      str(int(f_any)),
            })
            writer.writerow(row)

            # update prev
            prev[m] = (t, lat, lon, cog)

    print(f"Done → wrote {output_path}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", help="path to AIS CSV")
    p.add_argument("--output", "-o", default="flagged_stream.csv")
    args = p.parse_args()
    stream_flag(args.input_csv, args.output)