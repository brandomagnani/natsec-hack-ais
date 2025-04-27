#!/usr/bin/env python3
"""
avg_dt_per_mmsi.py
──────────────────
• Computes the mean time-interval (Δt, seconds) between successive AIS
  messages per MMSI.
• For MMSIs with a single sample, prints the exact transmission time.
• Saves results to CSV and, optionally, plots a histogram of all Δt values.
"""

import csv
import sys
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict

import matplotlib.pyplot as plt


def parse_iso(ts: str) -> datetime:
    """Return UTC-aware datetime from ISO string."""
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def compute(rows) -> Tuple[List[Tuple[str, float | None, datetime | None]],
                           float, int, List[float]]:
    """
    Returns:
        results  → list of (mmsi, mean_dt, lone_timestamp)
                   mean_dt is None for single-sample MMSIs.
                   lone_timestamp is None otherwise.
        max_dt   → longest Δt observed (seconds)
        n_ships  → total distinct MMSIs
        all_dts  → every Δt collected (for histogram)
    """
    by_mmsi: Dict[str, List[datetime]] = defaultdict(list)
    for row in rows:
        by_mmsi[row["MMSI"]].append(parse_iso(row["BaseDateTime"]))

    results, all_dts, max_dt = [], [], 0.0
    for mmsi, times in by_mmsi.items():
        times.sort()
        if len(times) < 2:
            results.append((mmsi, None, times[0]))
            continue

        deltas = [(t2 - t1).total_seconds() for t1, t2 in zip(times, times[1:])]
        mean_dt = sum(deltas) / len(deltas)
        all_dts.extend(deltas)
        max_dt = max(max_dt, max(deltas))
        results.append((mmsi, mean_dt, None))

    return results, max_dt, len(by_mmsi), all_dts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Input AIS CSV file (or '-' for stdin)")
    parser.add_argument("--out", default="avg_dt_results.csv",
                        help="Output CSV filename (default avg_dt_results.csv)")
    parser.add_argument("--plot", action="store_true",
                        help="Plot histogram of all Δt values")
    args = parser.parse_args()

    # ── read input ────────────────────────────────────────────────────────
    inp = sys.stdin if args.csv == "-" else open(args.csv, newline="")
    results, max_dt, n_ships, all_dts = compute(csv.DictReader(inp))
    if inp is not sys.stdin:
        inp.close()

    # ── write output csv ──────────────────────────────────────────────────
    out_path = Path(args.out)
    with out_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["MMSI", "mean_dt_seconds", "single_sample_timestamp_utc"])
        for mmsi, mean_dt, lone_ts in results:
            w.writerow([
                mmsi,
                f"{mean_dt:.2f}" if mean_dt is not None else "",
                lone_ts.isoformat() if lone_ts else ""
            ])

    # ── optional histogram ────────────────────────────────────────────────
    if args.plot and all_dts:
        plt.hist(all_dts, bins=50, color='steelblue', edgecolor='black')
        plt.title("Histogram of Δt (seconds)")
        plt.xlabel("Δt (seconds)")
        plt.ylabel("Frequency")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.show()

    # ── console summary ───────────────────────────────────────────────────
    print("MMSI         mean Δt (s)   | lone-sample timestamp (UTC)")
    print("-----------  ------------- | ---------------------------")
    for mmsi, mean_dt, lone_ts in sorted(results):
        if mean_dt is not None:
            print(f"{mmsi:11}  {mean_dt:13.2f}")
        else:
            print(f"{mmsi:11}                 | {lone_ts.isoformat()}")

    print(f"\n✓ results written to {out_path.resolve()}")
    print(f"Maximum Δt across all ships: {max_dt:.2f} seconds")
    print(f"Total distinct ships: {n_ships}")


if __name__ == "__main__":
    main()