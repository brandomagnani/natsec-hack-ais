#!/usr/bin/env python3
"""
Plot AIS tracks for every vessel whose name contains 'SURVEYOR'.

• Background: simple coastlines via Cartopy.
• Each vessel gets a unique colour + legend label.
• Printed list shows all matched vessel names.

Usage
-----
python plot_surveyor_world.py --csv AIS_2021_05_06.csv --out tracks.png
"""

from __future__ import annotations
import argparse
from pathlib import Path
import itertools

import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot *SURVEYOR* vessels on world map")
    p.add_argument("--csv", required=True, help="Input AIS CSV file")
    p.add_argument("--out", default=None, help="Save figure to PNG instead of showing")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.csv, low_memory=False)

    # --- filter names that contain 'SURVEYOR' -------------------------------
    mask = df["VesselName"].str.contains("SURVEYOR", case=False, na=False)
    matched = df.loc[mask, ["VesselName", "LAT", "LON"]]

    if matched.empty:
        print("No vessel names containing 'SURVEYOR' found.")
        return

    vessel_groups = matched.groupby("VesselName")
    vessel_names = list(vessel_groups.groups.keys())

    # --- print names --------------------------------------------------------
    print("Matched vessels:")
    for name in vessel_names:
        print(" •", name)

    # --- plotting -----------------------------------------------------------
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(11, 6))
    ax = plt.axes(projection=proj)
    ax.set_global()

    # coastline & land mask
    ax.add_feature(cfeature.LAND, facecolor="#f3f3f3")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)

    # colour cycle (repeat if > 10 vessels)
    colours = itertools.cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])

    for name, group in vessel_groups:
        lat = group["LAT"].values
        lon = group["LON"].values
        ax.scatter(lon, lat, s=3, transform=proj,
                   label=name, color=next(colours), alpha=0.75)

    ax.set_title("AIS positions – vessels containing “SURVEYOR”", fontsize=14)
    ax.legend(fontsize=8, loc="lower left", frameon=True, framealpha=0.9)

    if args.out:
        fig.savefig(args.out, dpi=150, bbox_inches="tight")
        print(f"Figure saved to {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
