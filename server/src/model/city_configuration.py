from pydantic import BaseModel


class TramStopPairCheck(BaseModel):
    source: int
    destination: int
    ratio: float


class CityConfiguration(BaseModel):
    osm_area_name: str
    gtfs_url: str
    ignored_gtfs_lines: list[str]
    custom_stop_mapping: dict[str, int]
    max_distance_ratio: float
    custom_tram_stop_pair_max_distance_checks: list[TramStopPairCheck]

    @property
    def custom_tram_stop_pair_ratio_map(self) -> dict[tuple[int, int], float]:
        return {
            (item.source, item.destination): item.ratio
            for item in self.custom_tram_stop_pair_max_distance_checks
        }
