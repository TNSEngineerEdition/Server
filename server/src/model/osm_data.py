from typing import Dict, List, Optional

from pydantic import BaseModel


class Way(BaseModel):
    id: int
    nodes: List[int]
    tags: Dict[str, str]


class TramStop(BaseModel):
    id: int
    lat: float
    lon: float
    name: Optional[str] = None


class NodeCoordinate(BaseModel):
    id: int
    lat: float
    lon: float


class TrackGeometryFeature(BaseModel):
    type: str
    properties: Dict
    geometry: Dict


class TrackGeometry(BaseModel):
    type: str
    features: List[TrackGeometryFeature]
