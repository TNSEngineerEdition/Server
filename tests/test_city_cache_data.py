import datetime
import shutil
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import Mock

import pytest

from city_data_builder import (
    CityDataBuilder,
    ResponseCityData,
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseTramRoute,
    ResponseTramTrip,
)
from city_data_cache import CityDataCache


class TestCityDataCache:
    @pytest.fixture(scope="class")
    def city_data_builder_mock(self) -> CityDataBuilder:
        result = Mock(spec=CityDataBuilder)

        result.tram_track_graph_data = [
            ResponseGraphNode(
                id=1,
                lat=50.0,
                lon=19.0,
                neighbors={
                    2: ResponseGraphEdge(
                        id=2, distance=100.0, azimuth=90.0, max_speed=5
                    )
                },
            )
        ]

        result.tram_routes_data = [
            ResponseTramRoute(
                name="1",
                background_color="",
                text_color="",
                trips=[ResponseTramTrip(trip_head_sign="Centrum", stops=[])],
            ),
        ]

        return result

    @pytest.fixture(scope="class")
    def cache_directory(self) -> Generator[Path, Any, None]:
        directory_path = Path(tempfile.mkdtemp())
        yield directory_path
        shutil.rmtree(directory_path)

    def test_store_and_load_data(
        self,
        cache_directory: Path,
        city_data_builder_mock: CityDataBuilder,
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory)
        city_id, date = "sample_city", datetime.date(2025, 9, 15)

        data = ResponseCityData(
            tram_track_graph=city_data_builder_mock.tram_track_graph_data,
            tram_routes=city_data_builder_mock.tram_routes_data,
        )

        # Act
        cache.store(city_id, date, data)
        loaded_data = cache.get(city_id, date)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert (
            loaded_data.tram_track_graph == city_data_builder_mock.tram_track_graph_data
        )
        assert loaded_data.tram_routes == city_data_builder_mock.tram_routes_data

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
        ]

    def test_remove_redundant_files(
        self, city_cache_dir: Path, krakow_response_city_data: ResponseCityData
    ) -> None:
        # Arrange
        cache = CityDataCache(cache_directory=city_cache_dir, max_file_count=2)
        krakow_dir = city_cache_dir / "krakow"
        initial_file_count = len([p for p in krakow_dir.iterdir()])

        # Act
        cache.store("krakow", datetime.date(2025, 9, 19), krakow_response_city_data)

        # Assert
        dates = [p.stem for p in krakow_dir.iterdir()]
        assert len(list(krakow_dir.iterdir())) == 2
        assert "2025-09-19" in dates
        assert len(dates) <= initial_file_count
