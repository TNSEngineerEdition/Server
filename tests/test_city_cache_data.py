import datetime
from pathlib import Path

from city_data_builder import (
    ResponseCityData,
)
from city_data_cache import CityDataCache


class TestCityDataCache:
    def test_get_data(
        self,
        city_cache_dir: Path,
        krakow_response_city_data: ResponseCityData,
    ) -> None:
        # Arrange
        cache = CityDataCache(city_cache_dir)
        city_id, date = "krakow", datetime.date(2025, 1, 1)

        # Act
        loaded_data = cache.get(city_id=city_id, date=date)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert loaded_data == krakow_response_city_data

    def test_store_data(
        self, city_cache_dir: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory=city_cache_dir)
        krakow_dir = city_cache_dir / "krakow"
        initial_file_count = len(list(krakow_dir.iterdir()))

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        # Assert
        dates = [p.stem for p in krakow_dir.iterdir()]
        assert "2025-09-19" in dates
        assert len(list(krakow_dir.iterdir())) == initial_file_count + 1

    def test_get_cached_dates(self, city_cache_dir: Path) -> None:
        # Arrange
        cache = CityDataCache(city_cache_dir, 10)

        # Act
        dates = cache.get_cached_dates("krakow")

        # Assert
        assert dates == [
            datetime.date(2025, 9, 14),
            datetime.date(2025, 9, 13),
            datetime.date(2025, 9, 12),
            datetime.date(2025, 9, 11),
            datetime.date(2025, 9, 4),
            datetime.date(2025, 1, 1),
        ]

    def test_store_remove_redundant_files(
        self, city_cache_dir: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory=city_cache_dir, max_file_count=2)
        krakow_dir = city_cache_dir / "krakow"
        initial_file_count = len(list(krakow_dir.iterdir()))

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        # Assert
        dates = [p.stem for p in krakow_dir.iterdir()]
        assert len(list(krakow_dir.iterdir())) == 2
        assert "2025-09-19" in dates
        assert len(dates) <= initial_file_count
