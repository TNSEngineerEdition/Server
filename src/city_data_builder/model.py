from pydantic import BaseModel, ConfigDict


class ResponseGraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    length: float
    azimuth: float
    max_speed: float


class ResponseGraphNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    lat: float
    lon: float
    neighbors: list[ResponseGraphEdge]


class ResponseGraphTramStop(ResponseGraphNode):
    name: str
    gtfs_stop_ids: list[str]


class ResponseTramTripStop(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    time: int


class ResponseTramTrip(BaseModel):
    model_config = ConfigDict(frozen=True)

    route: str
    trip_head_sign: str
    stops: list[ResponseTramTripStop]
