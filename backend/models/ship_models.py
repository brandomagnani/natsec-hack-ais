from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ShipData(BaseModel):
    timestamp: datetime
    long: float
    lat: float
    name: str
    ship_type: str

class ShipMovementData(BaseModel):
    timestamp: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    sog: Optional[float] = None
    cog: Optional[float] = None

class ShipMetadata(BaseModel):
    mmsi: Optional[str] = None
    basedatetime: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[float] = None
    vesselname: Optional[str] = None
    imo: Optional[str] = None
    callsign: Optional[str] = None
    vesseltype: Optional[int] = None
    status: Optional[int] = None
    length: Optional[int] = None
    width: Optional[int] = None
    draft: Optional[float] = None
    cargo: Optional[int] = None
    transceiverclass: Optional[str] = None
    activity: Optional[str] = None

class ShipDetailResponse(BaseModel):
    ship_metadata: ShipMetadata
    movement: List[ShipMovementData]
