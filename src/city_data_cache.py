import os
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from src.city_data_builder import (
    CityDataBuilder,
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramTrip,
)
from src.tram_stop_mapper import Weekday


class ResponseCityData(BaseModel):
    tram_track_graph: list[ResponseGraphNode | ResponseGraphTramStop]
    tram_trips: list[ResponseTramTrip]
    last_updated: datetime = Field(default_factory=datetime.now)


class CityDataCache:
    def __init__(
        self,
        cache_directory=Path(
            os.environ.get("CITY_DATA_CACHE_DIRECTORY", "./cache/cities")
        ),
        ttl_timedelta=timedelta(hours=24),
    ):
        self.cache_directory = cache_directory
        self.ttl_timedelta = ttl_timedelta

        self.cache_directory.mkdir(parents=True, exist_ok=True)

    def _get_path_to_cache(self, city_id: str, weekday: Weekday) -> Path:
        return self.cache_directory / f"{city_id}_{weekday}.json"

    def is_fresh(self, city_id: str, weekday: Weekday) -> bool:
        cache_file_path = self._get_path_to_cache(city_id, weekday)
        if not cache_file_path.is_file():
            return False

        timedelta_since_last_update = datetime.now() - datetime.fromtimestamp(
            cache_file_path.stat().st_mtime
        )

        return timedelta_since_last_update < self.ttl_timedelta

    def get(self, city_id: str, weekday: Weekday) -> ResponseCityData | None:
        cache_file_path = self._get_path_to_cache(city_id, weekday)
        if not cache_file_path.is_file():
            return None

        return ResponseCityData.model_validate_json(cache_file_path.read_text())

    def store(
        self,
        city_id: str,
        weekday: Weekday,
        city_data_builder: CityDataBuilder,
    ) -> None:
        data = ResponseCityData(
            tram_track_graph=city_data_builder.tram_track_graph_data,
            tram_trips=city_data_builder.tram_trips_data,
        )

        cache_file_path = self._get_path_to_cache(city_id, weekday)
        cache_file_path.write_text(data.model_dump_json())
