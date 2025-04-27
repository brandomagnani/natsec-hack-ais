#!/usr/bin/env python3
"""
save_tracks_to_folders_streaming.py
───────────────────────────────────
• Reads an AIS CSV in stream order (rows already time-sorted).
• Keeps every MMSI with at least --min fixes (default 200).
• Creates, for each kept vessel:

      data/<MMSI>/
          ├─ track.json   — ordered list of fixes
          └─ track.png    — auto-zoomed trajectory map

Memory footprint is tiny because no full track (nor the whole CSV)
is ever resident at once, and each line is appended with a
one-shot open/close so we never exceed the OS FD limit.
"""

from __future__ import annotations
import csv, json, argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List

import matplotlib
matplotlib.use("Agg")                    # headless backend
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from tqdm import tqdm


# ── utilities ──────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="AIS CSV file")
    p.add_argument("--min", type=int, default=200,
                   help="Minimum fixes per MMSI (default 200)")
    p.add_argument("--color", default="royalblue",
                   help="Polyline colour for PNG")
    return p.parse_args()


def read_rows(csv_path: Path) -> Iterator[dict]:
    with csv_path.open(newline="") as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            yield row


def plot_track(pts: list[dict], color: str, out_path: Path) -> None:
    lats = [p["lat"] for p in pts]
    lons = [p["lon"] for p in pts]

    fig, ax = plt.subplots(figsize=(6, 6))  # you can adjust figsize if needed
    ax.plot(lons, lats, marker="o", markersize=1, linewidth=0.5, color=color)

    # Set tight limits with a small margin (e.g., 0.01 degrees)
    margin = 0.01
    ax.set_xlim(min(lons) - margin, max(lons) + margin)
    ax.set_ylim(min(lats) - margin, max(lats) + margin)

    # Hide axis ticks and labels if you want a cleaner image
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")

    # Optional: tighter layout
    plt.tight_layout(pad=0)

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    csv_path  = Path(args.csv).expanduser()
    data_root = Path("data"); data_root.mkdir(exist_ok=True)

    # Pass 1: count fixes per MMSI, only if VesselName contains 'survey'
    print("Scanning once to count MMSIs …")
    counts: Counter[str] = Counter()
    vessel_names: dict[str, str] = {}  # To store MMSI -> VesselName mapping

    for row in tqdm(read_rows(csv_path), desc="Counting", unit="row"):
        vessel_name = row.get("VesselName", "").lower()
        if "survey" in vessel_name:
            mmsi = row["MMSI"]
            counts[mmsi] += 1
            vessel_names[mmsi] = vessel_name

    keep = {m for m, c in counts.items() if c >= args.min}
    print(f"Keeping {len(keep)} MMSIs with ≥{args.min} fixes and 'survey' in VesselName")

    # Pass 2: stream qualifying fixes to per-vessel JSONL (open-append-close)
    print("Writing qualifying tracks as JSONL …")
    for row in tqdm(read_rows(csv_path), desc="Streaming", unit="row"):
        m = row["MMSI"]
        if m not in keep:
            continue

        vessel_dir = data_root / m
        vessel_dir.mkdir(exist_ok=True)

        record = {
            "ts": row["BaseDateTime"],
            "lat": float(row["LAT"]),
            "lon": float(row["LON"]),
            "sog": row.get("SOG"),
            "cog": row.get("COG"),
        }

        # one-shot append ensures we hold zero lingering file-descriptors
        with (vessel_dir / "track.jsonl").open("a") as fh:
            fh.write(json.dumps(record) + "\n")

    # Pass 3: finalise JSON + draw PNGs
    print("Finalising JSON and drawing PNGs …")
    for m in tqdm(keep, desc="Rendering", unit="vessel"):
        vessel_dir = data_root / m
        jsonl_path = vessel_dir / "track.jsonl"

        with jsonl_path.open() as fh:
            pts = [json.loads(line) for line in fh]

        # pretty JSON
        (vessel_dir / "track.json").write_text(json.dumps(pts, indent=2))

        # trajectory PNG
        plot_track(pts, args.color, vessel_dir / "track.png")

        jsonl_path.unlink()   # delete intermediate file to save space

    print(f"\u2713 Saved {len(keep)} survey vessels into {data_root.resolve()}")


if __name__ == "__main__":
    main()
