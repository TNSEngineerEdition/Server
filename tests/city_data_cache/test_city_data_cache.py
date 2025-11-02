import datetime
import tempfile
from pathlib import Path
from typing import Generator
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from city_data_builder import ResponseCityData
from city_data_cache.city_data_cache import CityDataCache


class TestCityDataCache:
    @pytest.fixture
    def city_cache_directory(
        self, krakow_response_city_data: ResponseCityData
    ) -> Generator[Path, None, None]:
        response_city_data_str = krakow_response_city_data.model_dump_json()
        dates = ["2025-09-01", "2025-09-02", "2025-09-03", "2025-09-04", "2025-09-05"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            directory_path = Path(tmp_dir)

            with ZipFile(directory_path / "krakow.zip", "w", ZIP_DEFLATED) as zip_file:
                for date in dates:
                    zip_file.writestr(date, response_city_data_str)

            yield directory_path

    def test_get_data(
        self, city_cache_directory: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(city_cache_directory)
        city_id, date = "krakow", datetime.date(2025, 9, 1)

        # Act
        loaded_data = cache.get(city_id=city_id, date=date)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert loaded_data == krakow_response_city_data

    @pytest.mark.parametrize(
        ("city_id", "expected_file_count"),
        [
            pytest.param("krakow", 6, id="krakow"),
            pytest.param("some_city", 1, id="unknown_city"),
        ],
    )
    def test_store_data(
        self,
        city_cache_directory: Path,
        krakow_response_city_data: ResponseCityData,
        city_id: str,
        expected_file_count: int,
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory=city_cache_directory)

        # Act
        cache.store(city_id, datetime.date(2025, 9, 19), krakow_response_city_data)

        with ZipFile(city_cache_directory / f"{city_id}.zip") as zip_file:
            dates = zip_file.namelist()

        # Assert
        assert "2025-09-19" in dates
        assert len(dates) == expected_file_count

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
        self,
        city_cache_directory: Path,
        city_id: str,
        expected_dates: list[datetime.date],
    ) -> None:
        # Arrange
        cache = CityDataCache(city_cache_directory, 10)

        # Act
        dates = cache.get_cached_dates(city_id)

        # Assert
        assert dates == expected_dates

    def test_store_remove_redundant_files(
        self, city_cache_directory: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        max_file_count = 2

        cache = CityDataCache(
            cache_directory=city_cache_directory, max_file_count=max_file_count
        )
        krakow_zip = city_cache_directory / "krakow.zip"

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        with ZipFile(krakow_zip) as zip_file:
            dates = zip_file.namelist()

        # Assert
        assert len(dates) <= max_file_count
        assert "2025-09-19" in dates
