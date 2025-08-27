import os
from datetime import datetime, timedelta
from pathlib import Path

from city_data_builder import CityDataBuilder
from city_data_cache.model import ResponseCityData
from tram_stop_mapper import Weekday


class CityDataCache:
    def __init__(
        self,
        cache_directory: Path = Path(
            os.environ.get("CITY_DATA_CACHE_DIRECTORY", "./cache/cities")
        ),
        ttl_timedelta: timedelta = timedelta(hours=24),
    ) -> None:
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
            tram_routes=city_data_builder.tram_routes_data,
        )

        cache_file_path = self._get_path_to_cache(city_id, weekday)
        cache_file_path.write_text(data.model_dump_json())
