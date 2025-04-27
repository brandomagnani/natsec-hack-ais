#!/usr/bin/env python3
"""
plot_npy_polylines.py
---------------------
Visualise a NumPy polyline dump (object array) on a world map.

The .npy file must contain:  List[ List[ (lat, lon) ] ]

Usage
-----
python plot_npy_polylines.py  polylines.npy
python plot_npy_polylines.py  polylines.npy  --out trackmap.png
"""

from __future__ import annotations
import argparse
import itertools
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot polyline .npy dataset on world map.")
    p.add_argument("npy", help=".npy file created by make_polyline_dataset script")
    p.add_argument("--out", help="Save figure to PNG instead of showing")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    npy_path = Path(args.npy)

    polys = np.load(npy_path, allow_pickle=True)
    if len(polys) == 0:
        raise SystemExit("No polylines in file.")

    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(11, 6))
    ax = plt.axes(projection=proj)
    ax.set_global()

    # basic land/sea context
    ax.add_feature(cfeature.LAND, facecolor="#f2f2f2")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4)

    # colour cycle
    colours = itertools.cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])

    for idx, track in enumerate(polys, 1):
        lats, lons = zip(*track)
        ax.plot(lons, lats, linewidth=1.2, alpha=0.8,
                transform=proj, color=next(colours), label=f"poly {idx}")

    ax.set_title(f"{len(polys)} polylines from {npy_path.name}", fontsize=13)
    ax.legend(fontsize=7, loc="lower left")

    if args.out:
        fig.savefig(args.out, dpi=150, bbox_inches="tight")
        print(f"saved → {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
