from typing import List

from pydantic import BaseModel, Field


class TramStopPairCheck(BaseModel):
    from_: int = Field(alias="from")
    to: int
    ratio: float


class CityConfiguration(BaseModel):
    osm_area_name: str
    gtfs_url: str
    ignored_gtfs_lines: list[str]
    custom_stop_mapping: dict[str, int]
    max_distance_ratio: float
    custom_tram_stop_pair_max_distance_checks: List[TramStopPairCheck]
