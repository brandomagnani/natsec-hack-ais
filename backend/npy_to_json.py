import numpy as np
import json
import sys

# Define input and output filenames
npy_file = 'polylines_1.npy'
json_file = 'output.json'

print(f"Attempting to load {npy_file}...")

try:
    # Load the .npy file
    # allow_pickle=True is required for object arrays but can be insecure
    # if the file is from an untrusted source.
    data = np.load(npy_file, allow_pickle=True)
    print(f"Successfully loaded {npy_file}. Shape: {data.shape}, Dtype: {data.dtype}")

    # Flatten the list of polylines into a single list of points
    # Assuming data is structured like: [polyline1, polyline2, ...]
    # where polylineX = [point1, point2, ...]
    # and pointY = [x, y]
    # Convert each point (which might be an ndarray) to a list during flattening
    flattened_points = [point.tolist() for polyline in data for point in polyline]
    print(f"Flattened data structure. Original items: {len(data)}, Flattened points: {len(flattened_points)}")

    # Convert the flattened list to a list (it already is, but ensures compatibility if logic changes)
    data_list = list(flattened_points) # Using list() constructor for clarity
    print("Prepared flattened data for JSON serialization.")

    # Write the list to a JSON file
    print(f"Writing data to {json_file}...")
    with open(json_file, 'w') as f:
        json.dump(data_list, f, indent=4)
    print(f"Successfully converted {npy_file} to {json_file}")

except FileNotFoundError:
    print(f"Error: Input file '{npy_file}' not found.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)
    sys.exit(1)
