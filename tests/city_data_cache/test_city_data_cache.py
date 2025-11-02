import datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from city_data_builder import ResponseCityData
from city_data_cache.city_data_cache import CityDataCache


class TestCityDataCache:
    def test_get_data(
        self, city_cache_dir: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(city_cache_dir)
        city_id, date = "krakow", datetime.date(2025, 9, 1)

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
        krakow_zip = city_cache_dir / "krakow.zip"

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        with ZipFile(krakow_zip) as zip_file:
            dates = zip_file.namelist()

        # Assert
        assert "2025-09-19" in dates
        assert len(dates) == 6

    @pytest.mark.parametrize(
        ("city_id", "expected_dates"),
        [
            pytest.param(
                "krakow",
                [
                    datetime.date(2025, 9, 5),
                    datetime.date(2025, 9, 4),
                    datetime.date(2025, 9, 3),
                    datetime.date(2025, 9, 2),
                    datetime.date(2025, 9, 1),
                ],
                id="krakow",
            ),
            pytest.param("unknown_city", [], id="unknown_city"),
        ],
    )
    def test_get_cached_dates(
        self, city_cache_dir: Path, city_id: str, expected_dates: list[datetime.date]
    ) -> None:
        # Arrange
        cache = CityDataCache(city_cache_dir, 10)

        # Act
        dates = cache.get_cached_dates(city_id)

        # Assert
        assert dates == expected_dates

    def test_store_remove_redundant_files(
        self, city_cache_dir: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        max_file_count = 2

        cache = CityDataCache(
            cache_directory=city_cache_dir, max_file_count=max_file_count
        )
        krakow_zip = city_cache_dir / "krakow.zip"

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        with ZipFile(krakow_zip) as zip_file:
            dates = zip_file.namelist()

        # Assert
        assert len(dates) <= max_file_count
        assert "2025-09-19" in dates
