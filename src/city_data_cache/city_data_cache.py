import os
from datetime import timedelta
from pathlib import Path

from city_data_builder import CityConfiguration, CityDataBuilder
from city_data_cache.model import ResponseCityData


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

    # def is_fresh(self, city_id: str, weekday: Weekday) -> bool:
    #     cache_file_path = self._get_path_to_cache(city_id, weekday)
    #     if not cache_file_path.is_file():
    #         return False

    #     timedelta_since_last_update = datetime.now() - datetime.fromtimestamp(
    #         cache_file_path.stat().st_mtime
    #     )

    #     return timedelta_since_last_update < self.ttl_timedelta

    # def get(self, city_id: str, weekday: Weekday) -> ResponseCityData | None:
    #     cache_file_path = self._get_path_to_cache(city_id, weekday)
    #     if not cache_file_path.is_file():
    #         return None

    #     return ResponseCityData.model_validate_json(
    #         cache_file_path.read_text(encoding="utf-8")
    #     )

    def get(self, city_id: str, date: str) -> ResponseCityData | None:
        cache_file_path = self._get_path_to_cache(city_id, date)
        if not cache_file_path.is_file():
            return None

        return ResponseCityData.model_validate_json(
            cache_file_path.read_text(encoding="utf-8")
        )

    def get_all(self) -> dict[str, dict[str, CityConfiguration]]:
        return {
            city_dir.name: dict(
                sorted(
                    (
                        (city_by_date.stem, config)
                        for city_by_date in city_dir.iterdir()
                        if city_by_date.is_file()
                        and city_by_date.suffix == ".json"
                        and (
                            config := CityConfiguration.get_by_city_id_and_date(
                                city_dir.name, city_by_date.stem
                            )
                        )
                        is not None
                    ),
                    key=lambda date: date[0],
                    reverse=True,
                )
            )
            for city_dir in self.cache_directory.iterdir()
            if city_dir.is_dir()
        }

    def store(
        self,
        city_id: str,
        date: str,
        city_data_builder: CityDataBuilder,
    ) -> None:
        data = ResponseCityData(
            tram_track_graph=city_data_builder.tram_track_graph_data,
            tram_routes=city_data_builder.tram_routes_data,
        )

        cache_file_path = self._get_path_to_cache(city_id, date)
        cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        cache_file_path.write_text(data.model_dump_json())
