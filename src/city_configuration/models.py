from pydantic import BaseModel


class CustomTramStopPairMapping(BaseModel):
    source_gtfs_stop_id: str
    source_osm_node_id: int
    destination_gtfs_stop_id: str
    destination_osm_node_id: int


class TramStopPairCheck(BaseModel):
    source: int
    destination: int
    ratio: float
