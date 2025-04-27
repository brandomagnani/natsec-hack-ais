#!/usr/bin/env python3

import csv
import json
from pathlib import Path
from tqdm import tqdm

def find_ids(demo_data_dir: Path) -> set[str]:
    """Collect vessel IDs from DemoData subfolders."""
    ids = set()
    for subdir in demo_data_dir.iterdir():
        if subdir.is_dir():
            for vessel_dir in subdir.iterdir():
                if vessel_dir.is_dir():
                    ids.add(vessel_dir.name)
    return ids

def find_csv_files(*directories: Path) -> list[Path]:
    """Find all CSV files in given directories."""
    csv_files = []
    for directory in directories:
        csv_files.extend(directory.rglob("*.csv"))
    return csv_files

def process_csv(csv_path: Path, wanted_ids: set[str], collected: dict[str, dict]) -> None:
    """Stream a CSV file and collect metadata for wanted IDs."""
    with csv_path.open("r", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mmsi = row["MMSI"]
            if mmsi not in wanted_ids:
                continue
            if mmsi in collected:
                continue  # already found

            # collect stable fields
            collected[mmsi] = {
                "VesselName": row.get("VesselName", "").strip(),
                "IMO": row.get("IMO", "").strip(),
                "CallSign": row.get("CallSign", "").strip(),
                "VesselType": row.get("VesselType", "").strip(),
                "Length": row.get("Length", "").strip(),
                "Width": row.get("Width", "").strip(),
                "Draft": row.get("Draft", "").strip(),
                "Cargo": row.get("Cargo", "").strip(),
                "TransceiverClass": row.get("TransceiverClass", "").strip(),
            }

def save_metadata(demo_data_dir: Path, collected: dict[str, dict]) -> None:
    """Save metadata.json into each corresponding vessel folder."""
    for subdir in demo_data_dir.iterdir():
        if subdir.is_dir():
            for vessel_dir in subdir.iterdir():
                if vessel_dir.is_dir():
                    mmsi = vessel_dir.name
                    if mmsi in collected:
                        metadata_path = vessel_dir / "metadata.json"
                        metadata_path.write_text(json.dumps(collected[mmsi], indent=2))

def main():
    # CONFIGURATION
    demo_data_dir = Path("DemoData")
    csv_dir_1 = Path(".")  # <<< change me
    csv_dir_2 = Path("/Users/justin/Desktop/Hackathon/ais_2021_raw")  # <<< change me

    # Step 1: Gather vessel IDs
    ids = find_ids(demo_data_dir)
    print(f"Found {len(ids)} vessel IDs.")

    # Step 2: Find all CSVs
    csv_files = find_csv_files(csv_dir_1, csv_dir_2)
    print(f"Found {len(csv_files)} CSV files.")

    # Step 3: Process CSVs
    collected: dict[str, dict] = {}
    for csv_path in tqdm(csv_files, desc="Processing CSVs"):
        process_csv(csv_path, ids, collected)
        if len(collected) == len(ids):
            break  # early exit if all found

    print(f"Collected metadata for {len(collected)} vessels.")

    # Step 4: Save metadata.json
    save_metadata(demo_data_dir, collected)
    print("✓ Metadata saved.")

if __name__ == "__main__":
    main()
