import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.city_data_builder.city_data_builder import CityDataBuilder
from src.city_data_builder.model import (
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseTramTrip,
)
from src.city_data_cache import CityDataCache, ResponseCityData
from src.tram_stop_mapper import Weekday


class TestCityDataCache:
    @pytest.fixture(scope="class")
    def city_data_builder_mock(self) -> CityDataBuilder:
        result = Mock(spec=CityDataBuilder)

        result.tram_track_graph_data = [
            ResponseGraphNode(
                id=1,
                lat=50.0,
                lon=19.0,
                neighbors=[ResponseGraphEdge(id=2, length=100.0, azimuth=90.0)],
            )
        ]

        result.tram_trips_data = [
            ResponseTramTrip(route="1", trip_head_sign="Centrum", stops=[])
        ]

        return result

    @pytest.fixture(scope="class")
    def cache_directory(self):
        directory_path = Path(tempfile.mkdtemp())
        yield directory_path
        shutil.rmtree(directory_path)

    def test_is_cache_fresh_no_file(self, cache_directory: Path):
        # Arrange
        cache = CityDataCache(cache_directory, timedelta(hours=1))
        city_id, weekday = "sample_city", Weekday.MONDAY

        # Act
        is_fresh = cache.is_fresh(city_id, weekday)

        # Assert
        assert not is_fresh

    def test_store_and_load_data(
        self,
        cache_directory: Path,
        city_data_builder_mock: CityDataBuilder,
    ):
        # Arrange
        cache = CityDataCache(cache_directory, timedelta(hours=1))
        city_id, weekday = "sample_city", Weekday.MONDAY

        # Act
        cache.store(city_id, weekday, city_data_builder_mock)
        loaded_data = cache.get(city_id, weekday)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert (
            loaded_data.tram_track_graph == city_data_builder_mock.tram_track_graph_data
        )
        assert loaded_data.tram_trips == city_data_builder_mock.tram_trips_data
        assert cache.is_fresh(city_id, weekday)

    def test_is_cache_fresh_expired(
        self, cache_directory: Path, city_data_builder_mock: CityDataBuilder
    ):
        # Arrange
        cache = CityDataCache(cache_directory, timedelta())
        city_id, weekday = "sample_city", Weekday.MONDAY

        cache.store(city_id, weekday, city_data_builder_mock)

        # Sleeping so we're sure the cache expires
        time.sleep(1)

        # Act
        is_fresh = cache.is_fresh(city_id, weekday)

        # Assert
        assert not is_fresh
