#!/usr/bin/env python3
"""
Download daily NOAA AIS ZIP archives for a whole calendar year.

Usage examples
--------------
# Default (2021) …
python download_ais.py

# Specify another year …
python download_ais.py --year 2022         # or:  python download_ais.py 2022
"""

from __future__ import annotations
import argparse
import os
import sys
from datetime import date, timedelta

import requests
from tqdm import tqdm       # pip install tqdm

CHUNK   = 1024 * 1024        # 1 MiB
TIMEOUT = 60                 # seconds

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NOAA daily AIS ZIP archives for a given year."
    )
    parser.add_argument("year", nargs="?", default=2021, type=int,
                        help="Calendar year to download (default: 2021)")
    return parser.parse_args()

def download_one(day: date, dest_dir: str, base_url: str, overall: tqdm) -> None:
    fname = f"AIS_{day:%Y_%m_%d}.zip"
    url   = f"{base_url}/{fname}"
    path  = os.path.join(dest_dir, fname)

    if os.path.exists(path):            # already present
        overall.write(f"[SKIP] {fname}")
        overall.update(1)
        return

    try:
        resp = requests.get(url, stream=True, timeout=TIMEOUT)
        if resp.status_code != 200:
            overall.write(f"[MISS] {fname} – HTTP {resp.status_code}")
            overall.update(1)
            return

        total = int(resp.headers.get("Content-Length", 0))
        with open(path, "wb") as fp, tqdm(
            total=total, unit="B", unit_scale=True, unit_divisor=1024,
            desc=f"{fname}", position=1, leave=False
        ) as file_bar:
            for chunk in resp.iter_content(chunk_size=CHUNK):
                if chunk:
                    fp.write(chunk)
                    file_bar.update(len(chunk))

        overall.write(f"[ OK ] {fname}")
    except requests.RequestException as e:
        overall.write(f"[ERR] {fname} – {e}", file=sys.stderr)
    finally:
        overall.update(1)

def main() -> None:
    args     = parse_args()
    year     = args.year
    base_url = f"https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{year}"
    dest_dir = f"ais_{year}_zips"
    os.makedirs(dest_dir, exist_ok=True)

    start = date(year, 1, 1)
    end   = date(year, 12, 31)
    days  = (end - start).days + 1

    with tqdm(total=days, desc=f"{year} calendar days", position=0) as overall:
        current = start
        while current <= end:
            download_one(current, dest_dir, base_url, overall)
            current += timedelta(days=1)

if __name__ == "__main__":
    main()
