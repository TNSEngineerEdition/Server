import re
from functools import cached_property
from typing import Any

from pydantic import BaseModel, Field

from city_configuration.enums import TransitType

type StopMapping = int | tuple[int | None, int | None, int | None]


class CustomStopPairMapping(BaseModel):
    source_gtfs_stop_id: str
    source_osm_node_id: int
    destination_gtfs_stop_id: str
    destination_osm_node_id: int


class StopPairCheck(BaseModel):
    source: int
    destination: int
    ratio: float


class GTFSConfiguration(BaseModel):
    transit_type: TransitType
    file_url: str
    ignored_route_names: list[str] = Field(default_factory=list)
    custom_stop_mapping: dict[str, StopMapping] = Field(default_factory=dict)
    custom_stop_pair_mapping: list[CustomStopPairMapping] = Field(default_factory=list)
    ignored_node_conflicts: list[str] = Field(default_factory=list)
    stop_group_name_regex: str

    @cached_property
    def custom_stop_pair_by_gtfs_stop_ids(
        self,
    ) -> dict[tuple[str, str], tuple[int, int]]:
        return {
            (item.source_gtfs_stop_id, item.destination_gtfs_stop_id): (
                item.source_osm_node_id,
                item.destination_osm_node_id,
            )
            for item in self.custom_stop_pair_mapping
        }

    @cached_property
    def stop_group_name_pattern(self) -> re.Pattern[str]:
        return re.compile(self.stop_group_name_regex)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, GTFSConfiguration):
            return False

        return self.file_url == other.file_url

    def __hash__(self) -> int:
        return hash(self.file_url)
