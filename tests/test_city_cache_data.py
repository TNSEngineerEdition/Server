import os
import tempfile
from datetime import datetime, timedelta
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
    def temp_cache(self):
        cache_dir = Path(tempfile.mkdtemp())
        return CityDataCache(cache_dir=cache_dir, ttl_hours=1)

    @staticmethod
    def sample_data():
        tram_track_graph = [
            ResponseGraphNode(
                id=1,
                lat=50.0,
                lon=19.0,
                neighbors=[ResponseGraphEdge(id=2, length=100.0, azimuth=90.0)],
            )
        ]
        tram_trips = [ResponseTramTrip(route="1", trip_head_sign="Centrum", stops=[])]
        return tram_track_graph, tram_trips

    def test_cache_miss_if_no_file(self, temp_cache: CityDataCache):
        assert not temp_cache.is_cache_fresh("unknown_city")

    def test_store_and_load_data(self, temp_cache: CityDataCache):
        city_id = "sample_city"
        tram_track_graph, tram_trips = self.sample_data()

        stored_data = temp_cache.store_and_return(city_id, tram_track_graph, tram_trips)
        loaded_data = temp_cache.load_cached_data(city_id)

        assert isinstance(loaded_data, ResponseCityData)
        assert stored_data == loaded_data
        assert temp_cache.is_cache_fresh(city_id)

    def test_cache_expiry(self):
        cache_dir = Path(tempfile.mkdtemp())
        short_lived_cache = CityDataCache(cache_dir=cache_dir, ttl_hours=0)
        city_id = "old_city"
        tram_track_graph, tram_trips = self.sample_data()

        short_lived_cache.store_and_return(city_id, tram_track_graph, tram_trips)

        old_time = datetime.now() - timedelta(hours=1)
        path = short_lived_cache._get_path_to_cache(city_id)
        os.utime(path, (old_time.timestamp(), old_time.timestamp()))

        assert not short_lived_cache.is_cache_fresh(city_id)
