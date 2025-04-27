import json
import random
from typing import List
from fastapi import FastAPI, HTTPException
from routers import ship_routes
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Darkfleet Backend API",
    description="API for managing ship data.",
    version="0.1.0"
)

# Add CORS middleware
origins = [
    "*",  # Allows all origins for development. Restrict in production!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

app.include_router(ship_routes.router, prefix="/api/v1", tags=["ships"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Darkfleet API"}

# Define USA bounding box (latitude, longitude)
USA_BOUNDING_BOX = {
    "min_lat": 18.0,
    "max_lat": 72.0,
    "min_lon": -170.0,
    "max_lon": -60.0
}

def is_point_in_box(point: List[float], box: dict) -> bool:
    """Checks if a single point [lon, lat] is within the bounding box."""
    lon, lat = point
    return box["min_lat"] <= lat <= box["max_lat"] and \
           box["min_lon"] <= lon <= box["max_lon"]

@app.get("/cables", response_model=List[List[List[float]]])
async def get_cables():
    """
    Reads submarine cable coordinate data from a GeoJSON file.
    Returns a list of line strings that have at least one point within
    the defined USA bounding box.
    """
    try:
        # Use sync open in async context for simplicity here,
        # consider aiofiles for production performance
        with open("data/cable-geo.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cable data file not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing cable data file.")

    usa_nearby_line_strings: List[List[List[float]]] = []
    features = data.get("features", [])

    for feature in features:
        geometry = feature.get("geometry")
        if geometry and geometry.get("type") == "MultiLineString":
            multi_line_string_coords = geometry.get("coordinates")
            if multi_line_string_coords:
                for line_string in multi_line_string_coords:
                    is_near_usa = False
                    for point in line_string:
                        if is_point_in_box(point, USA_BOUNDING_BOX):
                            is_near_usa = True
                            break # Found a point in the box, no need to check others in this line string

                    if is_near_usa:
                        usa_nearby_line_strings.append(line_string)

    return usa_nearby_line_strings
