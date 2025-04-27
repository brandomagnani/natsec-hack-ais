#!/usr/bin/env python3
"""
Unzip every archive in ./ais_<YEAR>_zips to ./ais_<YEAR>_raw, then delete the
ZIP. Keeps the YYYY/MM/DD folder structure.

Usage
-----
# Default (2021)
python unzip_ais.py

# Another year
python unzip_ais.py --year 2022
"""

from __future__ import annotations
import argparse
import zipfile
from pathlib import Path

from tqdm import tqdm            # pip install tqdm

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract all ZIPs for a given year and delete originals."
    )
    parser.add_argument("year", nargs="?", default=2021, type=int,
                        help="Calendar year to process (default: 2021)")
    return parser.parse_args()

def unzip_and_delete(zip_path: Path, out_root: Path) -> None:
    # AIS_YYYY_MM_DD.zip  →  out_root/YYYY/MM/DD/*
    y, m, d = zip_path.stem.split("_")[1:]
    dest = out_root / y / m / d
    dest.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dest)
        zip_path.unlink()                     # delete after success
        tqdm.write(f"[ OK ] {zip_path.name}")
    except (zipfile.BadZipFile, OSError) as e:
        tqdm.write(f"[ERR] {zip_path.name} – {e}")

def main() -> None:
    args      = parse_args()
    year      = args.year
    zip_dir   = Path(f"ais_{year}_zips")
    out_root  = Path(f"ais_{year}_raw")

    zips = sorted(zip_dir.glob("*.zip"))
    if not zips:
        print(f"No .zip files found in {zip_dir}")
        return

    for zp in tqdm(zips, desc="Unzip + delete", unit="zip"):
        unzip_and_delete(zp, out_root)

if __name__ == "__main__":
    main()
