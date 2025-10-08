import datetime
import shutil
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest

from city_data_builder import (
    ResponseCityData,
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramRoute,
    ResponseTramTrip,
)
from city_data_cache.city_data_cache import CityDataCache


class TestCityDataCache:
    @pytest.fixture(scope="class")
    def response_city_data_mock(self) -> ResponseCityData:
        tram_graph: list[ResponseGraphNode | ResponseGraphTramStop] = [
            ResponseGraphNode(
                id=1,
                lat=50.0,
                lon=19.0,
                neighbors={
                    2: ResponseGraphEdge(
                        id=2, distance=100.0, azimuth=90.0, max_speed=5.0
                    )
                },
            ),
            ResponseGraphTramStop(
                id=2,
                lat=50.0005,
                lon=19.0005,
                name="Centrum",
                gtfs_stop_ids=["centrum_1"],
                neighbors={},
            ),
        ]

        tram_routes = [
            ResponseTramRoute(
                name="1",
                background_color="",
                text_color="",
                trips=[
                    ResponseTramTrip(
                        trip_head_sign="Centrum",
                        stops=[],
                    )
                ],
            )
        ]

        return ResponseCityData(tram_track_graph=tram_graph, tram_routes=tram_routes)

    @pytest.fixture(scope="class")
    def cache_directory(
        self, response_city_data_mock: ResponseCityData
    ) -> Generator[Path, Any, None]:
        directory_path = Path(tempfile.mkdtemp())
        cache = CityDataCache(directory_path)
        cache.store("krakow", datetime.date(2025, 1, 1), response_city_data_mock)
        yield directory_path
        shutil.rmtree(directory_path)

    def test_get_data(
        self, cache_directory: Path, response_city_data_mock: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory)
        city_id, date = "krakow", datetime.date(2025, 1, 1)

        # Act
        loaded_data = cache.get(city_id=city_id, date=date)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert loaded_data == response_city_data_mock

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
