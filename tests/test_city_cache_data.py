import tempfile
import time
from pathlib import Path

import pytest

from src.city_data_builder.model import (
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseTramTrip,
)
from src.city_data_cache import CityDataCache, ResponseCityData


class TestCityDataCache:
    @pytest.fixture
    def sample_data(self):
        tram_track_graph = [
            ResponseGraphNode(
                id=1,
                lat=50.0,
                lon=19.0,
                neighbors=[
                    ResponseGraphEdge(id=2, length=100.0, azimuth=90.0, max_speed=5)
                ],
            )
        ]
        tram_trips = [ResponseTramTrip(route="1", trip_head_sign="Centrum", stops=[])]
        return tram_track_graph, tram_trips

    def test_is_cache_fresh_no_file(self):
        # Arrange
        cache_dir = Path(tempfile.mkdtemp())
        cache = CityDataCache(cache_dir=cache_dir, ttl_hours=1)

        # Act
        is_fresh = cache.is_cache_fresh("unknown_city")

        # Assert
        assert not is_fresh

    def test_store_and_load_data(
        self, sample_data: tuple[list[ResponseGraphNode], list[ResponseTramTrip]]
    ):
        # Arrange
        cache_dir = Path(tempfile.mkdtemp())
        cache = CityDataCache(cache_dir=cache_dir, ttl_hours=1)
        city_id = "sample_city"
        tram_track_graph, tram_trips = sample_data

        # Act
        stored_data = cache.store_and_return(city_id, tram_track_graph, tram_trips)
        loaded_data = cache.load_cached_data(city_id)

        # Assert
        assert isinstance(loaded_data, ResponseCityData)
        assert stored_data == loaded_data
        assert cache.is_cache_fresh(city_id)

    def test_is_cache_fresh_expired(
        self, sample_data: tuple[list[ResponseGraphNode], list[ResponseTramTrip]]
    ):
        # Arrange
        cache_dir = Path(tempfile.mkdtemp())
        cache = CityDataCache(cache_dir=cache_dir, ttl_hours=0)
        city_id = "old_city"
        tram_track_graph, tram_trips = sample_data
        cache.store_and_return(city_id, tram_track_graph, tram_trips)

        # Sleeping so we're sure the cache expires
        time.sleep(1)

        # Act
        is_fresh = cache.is_cache_fresh(city_id)

        # Assert
        assert not is_fresh
