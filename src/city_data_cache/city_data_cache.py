import os
from datetime import timedelta
from pathlib import Path

from city_data_builder import CityConfiguration, CityDataBuilder
from city_data_cache.model import CachedCityDates, ResponseCityData


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

    def _get_path_to_cache(self, city_id: str, date: str) -> Path:
        return self.cache_directory / city_id / f"{date}.json"

    def get(self, city_id: str, date: str) -> ResponseCityData | None:
        cache_file_path = self._get_path_to_cache(city_id, date)
        if not cache_file_path.is_file():
            return None

        return ResponseCityData.model_validate_json(
            cache_file_path.read_text(encoding="utf-8")
        )

    def get_all_cached_dates(self) -> dict[str, CachedCityDates]:
        result: dict[str, CachedCityDates] = {}

        for city_dir in self.cache_directory.iterdir():
            if not city_dir.is_dir():
                continue
            city_id = city_dir.name
            cached_dates = []
            for city_by_date in city_dir.iterdir():
                if city_by_date.is_file() and city_by_date.suffix == ".json":
                    cached_dates.append(city_by_date.stem)

            cached_dates.sort(reverse=True)
            if (city_config := CityConfiguration.get_by_city_id(city_id)) is None:
                continue

            result[city_id] = {
                "city_configuration": city_config,
                "available_dates": cached_dates,
            }

        return result

    def build_and_store(
        self,
        city_id: str,
        date: str,
        to_cache: bool,
        city_data_builder: CityDataBuilder,
    ) -> ResponseCityData:
        data = ResponseCityData(
            tram_track_graph=city_data_builder.tram_track_graph_data,
            tram_routes=city_data_builder.tram_routes_data,
        )

        if not to_cache:
            return data

        cache_file_path = self._get_path_to_cache(city_id, date)
        cache_dir = cache_file_path.parent

        files_count = sum(1 for _ in cache_dir.iterdir()) if cache_dir.exists() else 0
        if files_count >= 10:
            return data

        cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        cache_file_path.write_text(data.model_dump_json(), encoding="utf-8")
        return data
