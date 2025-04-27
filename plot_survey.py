#!/usr/bin/env python3
"""
Plot tracks for vessels whose name contains 'SURVEYOR'.

Usage
-----
python plot_surveyor_tracks.py \
       --csv  AIS_2021_05_06.csv          # input file
       --out  surveyor_track.png          # (optional) save figure
       --save surveyor_points.csv         # (optional) write filtered rows
"""

from __future__ import annotations
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot AIS points for *SURVEYOR* ships.")
    p.add_argument("--csv",  required=True,  help="Input AIS CSV file")
    p.add_argument("--out",  default=None,   help="Filename for the plot (PNG)")
    p.add_argument("--save", default=None,   help="Save filtered rows to CSV")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 1. load – pandas handles >100-column AIS dumps fine
    df = pd.read_csv(args.csv, low_memory=False)

    # 2. filter rows whose VesselName contains 'SURVEYOR'
    mask = df["VesselName"].str.contains("SURVEYOR", case=False, na=False)
    surveyor_df = df.loc[mask, ["LAT", "LON"]]

    if surveyor_df.empty:
        print("No rows with 'SURVEYOR' in VesselName found.")
        return

    # 3. quick scatter plot
    plt.figure(figsize=(8, 6))
    plt.scatter(surveyor_df["LON"], surveyor_df["LAT"], s=2, alpha=0.6)
    plt.title("AIS positions – vessels containing 'SURVEYOR'")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid(True)

    if args.out:
        plt.savefig(args.out, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {args.out}")
    else:
        plt.show()

    # 4. optional: save the subset to its own CSV
    if args.save:
        surveyor_df.to_csv(args.save, index=False)
        print(f"Filtered rows written to {args.save}")


if __name__ == "__main__":
    main()
