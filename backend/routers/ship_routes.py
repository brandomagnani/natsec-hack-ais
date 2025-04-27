from fastapi import APIRouter, HTTPException
from models.ship_models import ShipData, ShipMovementData, ShipMetadata, ShipDetailResponse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from pydantic import ValidationError
import os
from pathlib import Path
import random

# --- Store Ship Metadata ---
# In a real application, this would likely come from a database or configuration
ship_metadata_store: Dict[str, Dict] = {
  "366823870": {
    "mmsi": "366823870",
    "basedatetime": "2024-08-31T00:00:00",
    "lat": 29.81678,
    "lon": -90.00590,
    "sog": 0.0,
    "cog": 246.9,
    "heading": 511.0,
    "vesselname": "MISS CLO",
    "imo": None,
    "callsign": "WDA5789",
    "vesseltype": 30,
    "status": 0,
    "length": 12,
    "width": 4,
    "draft": 0.0,
    "cargo": 30,
    "transceiverclass": "A",
    "activity": "normal"
  },
  "367375990": {
    "mmsi": "367375990",
    "basedatetime": "2024-08-31T00:00:00",
    "lat": 29.43567,
    "lon": -89.25963,
    "sog": 3.0,
    "cog": 358.6,
    "heading": 511.0,
    "vesselname": "SANTA MARIA IV",
    "imo": "IMO8940189",
    "callsign": "WDK8103",
    "vesseltype": 30,
    "status": None,
    "length": 27,
    "width": 8,
    "draft": None,
    "cargo": None,
    "transceiverclass": "B",
    "activity": "normal"
  },
  "367798420": {
    "mmsi": "367798420",
    "basedatetime": "2024-08-31T00:00:00",
    "lat": 40.70314,
    "lon": -74.00669,
    "sog": 3.7,
    "cog": 220.6,
    "heading": 44.0,
    "vesselname": "MCSHINY",
    "imo": None,
    "callsign": "WDJ6504",
    "vesseltype": 60,
    "status": 0,
    "length": 26,
    "width": 8,
    "draft": 2.0,
    "cargo": 60,
    "transceiverclass": "A",
    "activity": "normal"
  },
  "319246800": {
    "mmsi": "319246800",
    "basedatetime": "2024-08-31T00:00:00",
    "lat": 26.09787,
    "lon": -80.16670,
    "sog": 0.0,
    "cog": 360.0,
    "heading": 511.0,
    "vesselname": "OCN",
    "imo": "IMO0000000",
    "callsign": "ZGQK4",
    "vesseltype": 37,
    "status": None,
    "length": 24,
    "width": 12,
    "draft": None,
    "cargo": None,
    "transceiverclass": "B",
    "activity": "normal"
  },
  "368027920": {
    "mmsi": "368027920",
    "basedatetime": "2024-08-31T00:00:01",
    "lat": 41.19337,
    "lon": -71.58512,
    "sog": 0.2,
    "cog": 105.4,
    "heading": 511.0,
    "vesselname": "MONARCH",
    "imo": "IMO0000000",
    "callsign": "WDJ9635",
    "vesseltype": 36,
    "status": None,
    "length": 12,
    "width": 4,
    "draft": None,
    "cargo": None,
    "transceiverclass": "B",
    "activity": "normal"
  }
}

router = APIRouter()

DATA_DIR = Path("data") # Define the base data directory relative to the workspace root

def load_ship_data() -> List[ShipMetadata]:
    """
    Loads ship metadata from the /data directory structure.
    """
    print("Starting load_ship_data...") # Log start
    all_ships_metadata: List[ShipMetadata] = []
    data_dir_path = Path(DATA_DIR).resolve() # Get absolute path for clarity in logs
    print(f"Looking for data in directory: {data_dir_path}")

    if not data_dir_path.is_dir():
        print(f"Warning: Data directory '{data_dir_path}' not found or is not a directory.")
        return all_ships_metadata

    for activity_type_dir in data_dir_path.iterdir():
        if not activity_type_dir.is_dir():
            print(f"Skipping non-directory item in data folder: {activity_type_dir.name}")
            continue # Skip files like .DS_Store

        activity = activity_type_dir.name
        print(f"Processing activity directory: {activity}")
        if activity not in ["hydro", "malicious", "normal"]:
            print(f"Warning: Skipping unexpected directory in data folder: {activity_type_dir.name}")
            continue

        for ship_id_dir in activity_type_dir.iterdir():
            if not ship_id_dir.is_dir():
                print(f"Skipping non-directory item in activity folder '{activity}': {ship_id_dir.name}")
                continue

            ship_id = ship_id_dir.name # Extract ship_id for logging
            print(f"Processing ship ID directory: {ship_id} in {activity}")

            metadata_path = ship_id_dir / "metadata.json"
            track_path = ship_id_dir / "track.json"

            # Initialize metadata_data as empty dict in case metadata.json doesn't exist
            metadata_data = {}
            track_data = []

            # Load track.json first (if it exists) to potentially use for filling metadata
            if track_path.exists():
                print(f"Found track.json for {ship_id} in {activity}")
                try:
                    with open(track_path, 'r') as f:
                        track_data = json.load(f)
                        print(f"Successfully loaded track JSON for {ship_id} ({len(track_data)} records)")
                except json.JSONDecodeError as e:
                    print(f"Error decoding track JSON from {track_path}: {e}")
                    track_data = []
                except Exception as e:
                    print(f"Unexpected error loading track data for {ship_id}: {type(e).__name__} - {e}")
                    track_data = []

            # Load metadata.json if it exists
            if metadata_path.exists():
                print(f"Found metadata.json for {ship_id} in {activity}")
                try:
                    with open(metadata_path, 'r') as f:
                        metadata_data = json.load(f)
                        print(f"Successfully loaded metadata JSON for {ship_id}")

                    # --- Preprocessing Step ---
                    # Convert all field names to lowercase for consistency
                    metadata_data = {k.lower(): v for k, v in metadata_data.items()}
                    print(f"Converted all field names to lowercase for {ship_id}")

                    # Convert empty strings to None for optional numeric fields
                    if metadata_data.get('draft') == '':
                        print(f"Preprocessing: Converting empty draft to None for {ship_id}")
                        metadata_data['draft'] = None
                    if metadata_data.get('cargo') == '':
                        print(f"Preprocessing: Converting empty cargo to None for {ship_id}")
                        metadata_data['cargo'] = None
                    # Add similar checks for other optional numeric fields if needed

                    # Use the folder name as MMSI if it's missing in metadata
                    if not metadata_data.get('mmsi'):
                        print(f"Using directory name '{ship_id}' as MMSI for {ship_id}")
                        metadata_data['mmsi'] = ship_id

                    # Fill in missing metadata fields from track data if available
                    if track_data and len(track_data) > 0:
                        first_track = track_data[0]

                        # Use first track point's timestamp for basedatetime if missing
                        if 'basedatetime' not in metadata_data or metadata_data['basedatetime'] is None:
                            metadata_data['basedatetime'] = first_track.get('ts')
                            print(f"Using first track point's timestamp for basedatetime for {ship_id}")

                        # Fill lat/lon if missing in metadata
                        if 'lat' not in metadata_data or metadata_data['lat'] is None:
                            metadata_data['lat'] = first_track.get('lat')
                            print(f"Using first track point's lat for {ship_id}")
                        if 'lon' not in metadata_data or metadata_data['lon'] is None:
                            metadata_data['lon'] = first_track.get('lon')
                            print(f"Using first track point's lon for {ship_id}")
                        # Fill sog/cog if missing in metadata
                        if 'sog' not in metadata_data or metadata_data['sog'] is None:
                            # Convert to float if it's a string
                            sog_value = first_track.get('sog')
                            if isinstance(sog_value, str):
                                try:
                                    sog_value = float(sog_value)
                                except (ValueError, TypeError):
                                    sog_value = 0.0
                            metadata_data['sog'] = sog_value
                            print(f"Using first track point's sog for {ship_id}")
                        if 'cog' not in metadata_data or metadata_data['cog'] is None:
                            # Convert to float if it's a string
                            cog_value = first_track.get('cog')
                            if isinstance(cog_value, str):
                                try:
                                    cog_value = float(cog_value)
                                except (ValueError, TypeError):
                                    cog_value = 0.0
                            metadata_data['cog'] = cog_value
                            print(f"Using first track point's cog for {ship_id}")

                    # Add the activity field derived from the folder path
                    metadata_data['activity'] = activity
                    print(f"Added activity '{activity}' to metadata for {ship_id}")

                    # Validate and append
                    ship_metadata = ShipMetadata(**metadata_data)
                    all_ships_metadata.append(ship_metadata)
                    print(f"Successfully validated and added metadata for {ship_id}")

                except json.JSONDecodeError as e:
                    # Log error for corrupted metadata file
                    print(f"Error decoding JSON from {metadata_path}: {e}")
                except ValidationError as e: # Catch Pydantic validation errors specifically
                    print(f"Validation Error processing {metadata_path}: {e}")
                except Exception as e: # Catch other potential errors
                    print(f"Unexpected Error processing {metadata_path}: {type(e).__name__} - {e}")
            else:
                 # Log if metadata.json is missing
                 print(f"Warning: metadata.json not found in {ship_id_dir}")

                 # If metadata.json is missing but track.json exists, create metadata from the first track point
                 if track_data and len(track_data) > 0:
                     print(f"Creating metadata from track data for {ship_id}")
                     first_track = track_data[0]

                     # Convert string values to appropriate types
                     sog_value = first_track.get('sog', 0.0)
                     if isinstance(sog_value, str):
                         try:
                             sog_value = float(sog_value)
                         except (ValueError, TypeError):
                             sog_value = 0.0

                     cog_value = first_track.get('cog', 0.0)
                     if isinstance(cog_value, str):
                         try:
                             cog_value = float(cog_value)
                         except (ValueError, TypeError):
                             cog_value = 0.0

                     # Create basic metadata from track
                     metadata_data = {
                         'mmsi': ship_id,
                         'lat': first_track.get('lat'),
                         'lon': first_track.get('lon'),
                         'sog': sog_value,
                         'cog': cog_value,
                         'activity': activity,
                         # Set basedatetime from the track's timestamp
                         'basedatetime': first_track.get('ts')
                     }

                     try:
                         # Validate and append
                         ship_metadata = ShipMetadata(**metadata_data)
                         all_ships_metadata.append(ship_metadata)
                         print(f"Successfully created metadata from track for {ship_id}")
                     except ValidationError as e:
                         print(f"Validation Error creating metadata from track for {ship_id}: {e}")
                     except Exception as e:
                         print(f"Unexpected Error creating metadata from track for {ship_id}: {type(e).__name__} - {e}")

            # No need to continue if both files are missing
            if not metadata_path.exists() and not track_path.exists():
                print(f"Both metadata.json and track.json missing for {ship_id}, skipping...")

    print(f"Finished load_ship_data. Total ships loaded: {len(all_ships_metadata)}") # Log end
    return all_ships_metadata


@router.get("/ships", response_model=List[ShipMetadata], tags=["ships"])
async def get_all_ships():
    """
    Retrieves metadata for all ships from the data directory.
    Includes the activity type (hydro, malicious, normal) based on folder structure.
    """
    try:
        ship_data = load_ship_data()

        # Sort the data to place "malicious" and "hydro" ships randomly between indices 5 and 20
        if ship_data and len(ship_data) > 5:
            # Split ships by activity type
            normal_ships = [ship for ship in ship_data if ship.activity == "normal"]
            malicious_ships = [ship for ship in ship_data if ship.activity == "malicious"]
            hydro_ships = [ship for ship in ship_data if ship.activity == "hydro"]

            print(f"Ship counts - Normal: {len(normal_ships)}, Malicious: {len(malicious_ships)}, Hydro: {len(hydro_ships)}")

            # Shuffle the malicious and hydro ships
            special_ships = malicious_ships + hydro_ships
            random.shuffle(special_ships)

            # Determine where to place special ships
            max_index = min(20, len(ship_data))  # Don't go beyond the end of the list
            min_index = min(5, len(normal_ships))  # Make sure we have room for normal ships first

            # Construct the final list
            # First place normal ships at the beginning
            result = []
            if normal_ships:
                result.extend(normal_ships)

            # Then insert special ships at random positions between min_index and max_index
            for i, ship in enumerate(special_ships):
                if i + min_index < max_index:
                    insert_index = random.randint(min_index, max_index - 1)
                    # Extend the list if needed
                    while len(result) <= insert_index:
                        result.append(None)

                    # Insert the ship, or replace None if already extended
                    if result[insert_index] is None:
                        result[insert_index] = ship
                    else:
                        result.insert(insert_index, ship)
                else:
                    # If we've run out of positions in the range, append to the end
                    result.append(ship)

            # Remove any None values that might remain
            result = [ship for ship in result if ship is not None]

            # Add any remaining ships to the end
            all_ships_set = set(s.mmsi for s in result if s.mmsi)
            for ship in ship_data:
                if ship.mmsi and ship.mmsi not in all_ships_set:
                    result.append(ship)

            print(f"Reordered ships - Total before: {len(ship_data)}, Total after: {len(result)}")
            ship_data = result

        # No need to check if ship_data is empty, returning an empty list is valid
        return ship_data
    except Exception as e:
        # Log the exception details
        print(f"Error loading ship data: {e}") # Consider using proper logging
        raise HTTPException(status_code=500, detail="Internal server error loading ship data")

@router.get("/ship-detail/{ship_id}", response_model=ShipDetailResponse)
async def get_ship_detail(ship_id: str) -> ShipDetailResponse:
    """Returns detailed movement data and metadata for a specific ship_id (MMSI)."""
    # Try to find the ship in the data directory first
    found = False
    activity_type = None
    ship_track = []
    metadata_obj = None

    # Look through data directory for this ship
    for activity in ["hydro", "malicious", "normal"]:
        ship_dir = DATA_DIR / activity / ship_id
        if ship_dir.is_dir():
            found = True
            activity_type = activity

            # Load metadata
            metadata_path = ship_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata_data = json.load(f)

                    # Process metadata
                    metadata_data = {k.lower(): v for k, v in metadata_data.items()}

                    # Convert empty strings to None
                    if metadata_data.get('draft') == '':
                        metadata_data['draft'] = None
                    if metadata_data.get('cargo') == '':
                        metadata_data['cargo'] = None

                    # Ensure MMSI and activity are set
                    if not metadata_data.get('mmsi'):
                        metadata_data['mmsi'] = ship_id
                    metadata_data['activity'] = activity

                    # Create metadata object
                    metadata_obj = ShipMetadata(**metadata_data)
                except Exception as e:
                    print(f"Error loading metadata for ship {ship_id} in {activity}: {e}")

            # Load track data
            track_path = ship_dir / "track.json"
            if track_path.exists():
                try:
                    with open(track_path, 'r') as f:
                        track_data = json.load(f)

                    # Convert track data to ShipMovementData objects
                    for point in track_data:
                        # Handle possible string values for numeric fields
                        sog = point.get('sog', 0.0)
                        if isinstance(sog, str):
                            try:
                                sog = float(sog)
                            except (ValueError, TypeError):
                                sog = 0.0

                        cog = point.get('cog', 0.0)
                        if isinstance(cog, str):
                            try:
                                cog = float(cog)
                            except (ValueError, TypeError):
                                cog = 0.0

                        ship_track.append(ShipMovementData(
                            timestamp=point.get('ts'),
                            lat=point.get('lat'),
                            lon=point.get('lon'),
                            sog=sog,
                            cog=cog
                        ))
                except Exception as e:
                    print(f"Error loading track data for ship {ship_id} in {activity}: {e}")

            # If we have metadata but no track, or have track but no metadata, handle accordingly
            if not metadata_obj and ship_track:
                # Create metadata from first track point if we have track but no metadata
                first_point = ship_track[0]
                metadata_obj = ShipMetadata(
                    mmsi=ship_id,
                    lat=first_point.lat,
                    lon=first_point.lon,
                    sog=first_point.sog,
                    cog=first_point.cog,
                    activity=activity,
                    basedatetime=first_point.timestamp
                )

            # Break once we've found the ship
            break

    # If not found in data directory, fall back to in-memory store
    if not found:
        # --- Get Metadata from in-memory store ---
        metadata_dict = ship_metadata_store.get(ship_id)
        if not metadata_dict:
            raise HTTPException(status_code=404, detail=f"Ship metadata not found for MMSI: {ship_id}")

        # Convert all field names to lowercase for consistency
        metadata_dict_lower = {k.lower(): v for k, v in metadata_dict.items()}
        # Add activity field if it's not present
        if 'activity' not in metadata_dict_lower:
            metadata_dict_lower['activity'] = 'normal'  # Default activity

        # Validate and create the metadata object
        metadata_obj = ShipMetadata(**metadata_dict_lower)

        # --- Create Mock Movement Data ---
        start_time = datetime(2024, 1, 1, 10, 0, 0) # Base time for timestamp generation

        if ship_id == "366823870": # Specific logic for the ship using output.json
            try:
                with open('output.json', 'r') as f:
                    coordinates = json.load(f)
                # Generate ShipMovementData using coordinates from output.json
                for i, coord in enumerate(coordinates):
                    ts = start_time + timedelta(minutes=i*5)
                    ship_track.append(ShipMovementData(
                        timestamp=ts,
                        lat=coord[0],
                        lon=coord[1],
                        sog=0.0,
                        cog=0.0
                    ))
            except Exception as e:
                print(f"Error loading output.json for ship {ship_id}: {e}")
        else:
            # --- Use Mock Movement Data for other known ships ---
            mock_start_long = metadata_dict_lower.get("lon", 118.5)
            mock_start_lat = metadata_dict_lower.get("lat", 24.0)

            # Create mock track data
            for i in range(3):
                ts = start_time + timedelta(minutes=i*5)
                ship_track.append(ShipMovementData(
                    timestamp=ts,
                    lat=mock_start_lat + (0.03 * i),
                    lon=mock_start_long + (0.05 * i),
                    sog=metadata_dict_lower.get("sog", 0.0),
                    cog=metadata_dict_lower.get("cog", 0.0)
                ))

    # Ensure we have both metadata and track data
    if not metadata_obj:
        raise HTTPException(status_code=404, detail=f"Ship metadata not found for MMSI: {ship_id}")

    # Create the final response object
    response = ShipDetailResponse(ship_metadata=metadata_obj, movement=ship_track)
    return response
