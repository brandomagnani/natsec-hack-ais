#!/usr/bin/env python3

from pathlib import Path
import json

def get_ids(folder: Path) -> set[str]:
    """Get set of vessel IDs (folder names) in a subfolder."""
    return {f.name for f in folder.iterdir() if f.is_dir()}

def main():
    # CONFIGURATION
    demo_data_dir = Path("DemoData")
    subfolders = [f for f in demo_data_dir.iterdir() if f.is_dir()]
    if len(subfolders) != 3:
        raise ValueError(f"Expected exactly 3 folders inside {demo_data_dir}, found {len(subfolders)}.")

    folder1, folder2, folder3 = subfolders
    ids1 = get_ids(folder1)
    ids2 = get_ids(folder2)
    ids3 = get_ids(folder3)

    # Set operations
    all_ids = ids1 | ids2 | ids3
    common_12 = ids1 & ids2
    common_13 = ids1 & ids3
    common_23 = ids2 & ids3
    common_all = ids1 & ids2 & ids3

    unique_1 = ids1 - (ids2 | ids3)
    unique_2 = ids2 - (ids1 | ids3)
    unique_3 = ids3 - (ids1 | ids2)

    print(f"Summary:")
    print(f"- {folder1.name}: {len(ids1)} IDs")
    print(f"- {folder2.name}: {len(ids2)} IDs")
    print(f"- {folder3.name}: {len(ids3)} IDs")
    print(f"- Total unique IDs across all: {len(all_ids)}\n")

    print(f"Shared between {folder1.name} and {folder2.name}: {len(common_12)}")
    print(f"Shared between {folder1.name} and {folder3.name}: {len(common_13)}")
    print(f"Shared between {folder2.name} and {folder3.name}: {len(common_23)}")
    print(f"Shared between all three folders: {len(common_all)}\n")

    print(f"IDs unique to {folder1.name}: {len(unique_1)}")
    print(f"IDs unique to {folder2.name}: {len(unique_2)}")
    print(f"IDs unique to {folder3.name}: {len(unique_3)}")

    # (Optional) Save detailed lists if needed
    (demo_data_dir / "id_analysis.json").write_text(
        json.dumps({
            "unique_to_" + folder1.name: sorted(unique_1),
            "unique_to_" + folder2.name: sorted(unique_2),
            "unique_to_" + folder3.name: sorted(unique_3),
            "common_between_" + folder1.name + "_" + folder2.name: sorted(common_12),
            "common_between_" + folder1.name + "_" + folder3.name: sorted(common_13),
            "common_between_" + folder2.name + "_" + folder3.name: sorted(common_23),
            "common_all_three": sorted(common_all),
        }, indent=2)
    )
    print("\n✓ Detailed ID analysis saved to id_analysis.json.")

if __name__ == "__main__":
    main()