import datetime
import os
from pathlib import Path

from city_data_builder import ResponseCityData


class CityDataCache:
    DEFAULT_CACHE_DIRECTORY = Path(
        os.environ.get("CITY_DATA_CACHE_DIRECTORY", "./cache/cities")
    )
    DEFAULT_MAX_FILE_COUNT = int(os.environ.get("CITY_DATA_CACHE_MAX_FILE_COUNT", "10"))

    def __init__(
        self,
        cache_directory: Path = DEFAULT_CACHE_DIRECTORY,
        max_file_count: int = DEFAULT_MAX_FILE_COUNT,
    ) -> None:
        self.cache_directory = cache_directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.max_file_count = max_file_count

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

    def get_cached_dates(self, city_id: str) -> list[datetime.date]:
        return sorted(
            [
                datetime.date.fromisoformat(city_by_date.stem)
                for city_by_date in self._get_path_to_city_cache(city_id).iterdir()
                if city_by_date.is_file() and city_by_date.suffix == ".json"
            ],
            reverse=True,
        )

    def _remove_redundant_files(self, city_cache_dir: Path) -> None:
        file_count = len(list(city_cache_dir.iterdir()))
        if file_count < self.max_file_count:
            return

        to_remove = file_count - self.max_file_count + 1
        files = [
            file
            for file in city_cache_dir.iterdir()
            if file.is_file() and file.suffix == ".json"
        ]

        files.sort(key=lambda file: file.stem)

        for file in files[:to_remove]:
            file.unlink()

    def store(
        self,
        city_id: str,
        date: datetime.date,
        city_data: ResponseCityData,
    ) -> ResponseCityData:
        cache_file_path = self._get_path_to_cache_for_file(city_id, date)

        if not cache_file_path.parent.exists():
            cache_file_path.parent.mkdir(parents=True, exist_ok=True)

        self._remove_redundant_files(cache_file_path.parent)

        cache_file_path.write_text(city_data.model_dump_json(), encoding="utf-8")
        return city_data
