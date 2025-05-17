from functools import cached_property
from pathlib import Path

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


class CityConfiguration(BaseModel):
    osm_area_name: str
    gtfs_url: str
    ignored_gtfs_lines: list[str]
    custom_stop_mapping: dict[str, int | tuple[int | None, int | None, int | None]]
    custom_stop_pair_mapping: list[CustomTramStopPairMapping]
    max_distance_ratio: float
    custom_tram_stop_pair_max_distance_checks: list[TramStopPairCheck]

    @cached_property
    def custom_tram_stop_pair_ratio_map(self) -> dict[tuple[int, int], float]:
        return {
            (item.source, item.destination): item.ratio
            for item in self.custom_tram_stop_pair_max_distance_checks
        }

    @cached_property
    def custom_stop_pair_by_gtfs_stop_ids(self):
        return {
            (item.source_gtfs_stop_id, item.destination_gtfs_stop_id): (
                item.source_osm_node_id,
                item.destination_osm_node_id,
            )
            for item in self.custom_stop_pair_mapping
        }

    @classmethod
    def from_path(cls, path: Path):
        return cls.model_validate_json(path.read_text())
