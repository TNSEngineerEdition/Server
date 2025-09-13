import datetime
import os
from pathlib import Path

from city_data_builder import CityConfiguration, ResponseCityData
from city_data_cache.model import CachedCityDates


class CityDataCache:
    def __init__(
        self,
        cache_directory: Path = Path(
            os.environ.get("CITY_DATA_CACHE_DIRECTORY", "./cache/cities")
        ),
        max_file_count: int = 10,
    ) -> None:
        self.cache_directory = cache_directory
        self.max_file_count = max_file_count

        self.cache_directory.mkdir(parents=True, exist_ok=True)

    def _get_path_to_cache_for_file(self, city_id: str, date: datetime.date) -> Path:
        return self.cache_directory / city_id / f"{date.isoformat()}.json"

    def _get_path_to_city_cache(self, city_id: str) -> Path:
        return self.cache_directory / city_id

    def get(self, city_id: str, date: datetime.date) -> ResponseCityData | None:
        cache_file_path = self._get_path_to_cache_for_file(city_id, date)
        if not cache_file_path.is_file():
            return None

        return ResponseCityData.model_validate_json(
            cache_file_path.read_text(encoding="utf-8")
        )

    def _get_cached_dates(self, city_id: str) -> list[datetime.date]:
        cached_dates: list[datetime.date] = []
        city_dir = self._get_path_to_city_cache(city_id)
        for city_by_date in city_dir.iterdir():
            if city_by_date.is_file() and city_by_date.suffix == ".json":
                cached_dates.append(datetime.date.fromisoformat(city_by_date.stem))

        return sorted(cached_dates, reverse=True)

    def get_all_cached_dates(self) -> dict[str, CachedCityDates]:
        result: dict[str, CachedCityDates] = {}

        for city_dir in self.cache_directory.iterdir():
            if not city_dir.is_dir():
                continue
            city_id = city_dir.name
            cached_dates = self._get_cached_dates(city_id)
            if (
                city_config := CityConfiguration.get_by_city_id(city_id)
            ) is None or not cached_dates:
                continue

            result[city_id] = {
                "city_configuration": city_config,
                "available_dates": cached_dates,
            }

        return result

    def _remove_the_oldest_one(self, city_cache_dir: Path) -> None:
        oldest_file = min(
            cached_file
            for cached_file in city_cache_dir.iterdir()
            if cached_file.is_file() and cached_file.suffix == ".json"
        )

        oldest_file.unlink()

    def store(
        self,
        city_id: str,
        date: datetime.date,
        city_data: ResponseCityData,
    ) -> ResponseCityData:

        cache_file_path = self._get_path_to_cache_for_file(city_id, date)
        cache_dir = self._get_path_to_city_cache(city_id)

        files_count = sum(1 for _ in cache_dir.iterdir()) if cache_dir.exists() else 0
        if files_count >= self.max_file_count:
            self._remove_the_oldest_one(cache_dir)

        cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        cache_file_path.write_text(city_data.model_dump_json(), encoding="utf-8")
        return city_data
