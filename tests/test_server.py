import logging
import urllib.parse
from unittest.mock import MagicMock, patch

import overpy
import pytest
from fastapi.testclient import TestClient

from src.city_data_builder.city_configuration import CityConfiguration
from src.server import app
from src.tram_stop_mapper import GTFSPackage


class TestServer:
    client = TestClient(app)

    def test_cities(self):
        # Act
        response = self.client.get("/cities")
        cities = response.json()

        # Assert
        assert response.status_code == 200
        assert isinstance(cities, dict)

        for city_id, city_configuration in cities.items():
            assert city_id
            assert isinstance(city_id, str)

            osm_area_name = city_configuration["osm_area_name"]
            assert osm_area_name
            assert isinstance(osm_area_name, str)

            gtfs_url = city_configuration["gtfs_url"]
            assert gtfs_url
            assert isinstance(gtfs_url, str)

            url_parse_result = urllib.parse.urlparse(gtfs_url)
            assert url_parse_result.scheme
            assert url_parse_result.netloc

            ignored_gtfs_lines = city_configuration["ignored_gtfs_lines"]
            assert isinstance(ignored_gtfs_lines, list)
            assert all(isinstance(line, str) for line in ignored_gtfs_lines)
            assert len(set(ignored_gtfs_lines)) == len(ignored_gtfs_lines)

            custom_stop_mapping = city_configuration["custom_stop_mapping"]
            assert isinstance(custom_stop_mapping, dict)
            assert all(
                isinstance(gtfs_stop_id, str) for gtfs_stop_id in custom_stop_mapping
            )
            assert all(
                isinstance(osm_node_id, (int, list))
                for osm_node_id in custom_stop_mapping.values()
            )

        assert any(
            city_configuration["osm_area_name"] == "Kraków"
            for city_configuration in cities.values()
        )

    @patch("pathlib.Path.read_text", return_value="{Malformed json")
    def test_cities_validation_error(
        self, read_text_mock: MagicMock, caplog: pytest.LogCaptureFixture
    ):
        # Act
        with caplog.at_level(logging.ERROR, logger="src.server"):
            response = self.client.get("/cities")

        # Assert
        assert response.status_code == 500
        assert response.json()["detail"] == "Invalid configuration files"

        assert "Invalid configuration file: " in caplog.text
        assert "ValidationError" in caplog.text

    @patch("src.city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("src.tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("src.overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("src.overpass_client.OverpassClient.get_relations_and_stops")
    @patch("src.city_data_cache.CityDataCache.is_fresh", return_value=False)
    def test_get_city_data(
        self,
        cache_is_fresh_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_latest_in_directory_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        krakow_city_configuration: CityConfiguration,
    ):
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package
        get_latest_in_directory_mock.return_value = krakow_city_configuration

        # Act
        response = self.client.get("/cities/krakow")
        city_data = response.json()

        # Assert
        assert response.status_code == 200
        assert isinstance(city_data, dict)

        tram_track_graph = city_data["tram_track_graph"]
        assert tram_track_graph
        assert isinstance(tram_track_graph, list)

        for tram_track_node in tram_track_graph:
            node_id = tram_track_node["id"]
            assert node_id
            assert isinstance(node_id, int)

            assert isinstance(tram_track_node["lat"], float)
            assert isinstance(tram_track_node["lon"], float)

            neighbors = tram_track_node["neighbors"]
            assert isinstance(neighbors, list)
            for neighbor in neighbors:
                assert isinstance(neighbor, dict)

                neighbor_id = neighbor["id"]
                assert neighbor_id
                assert isinstance(neighbor_id, int)

                neighbor_length = neighbor["length"]
                assert neighbor_length
                assert isinstance(neighbor_length, float)

                neighbor_azimuth = neighbor["azimuth"]
                assert isinstance(neighbor_azimuth, float)
                assert -180 <= neighbor_azimuth <= 180

            if "name" in tram_track_node or "gtfs_stop_ids" in tram_track_node:
                assert isinstance(tram_track_node["name"], str)

                gtfs_stop_ids = tram_track_node["gtfs_stop_ids"]
                assert isinstance(gtfs_stop_ids, list)
                assert all(isinstance(item, str) for item in gtfs_stop_ids)

        assert any(
            ("name" in tram_track_node or "gtfs_stop_ids" in tram_track_node)
            for tram_track_node in tram_track_graph
        )

        tram_trips = city_data["tram_trips"]
        assert tram_trips
        assert isinstance(tram_trips, list)

        for tram_trip in tram_trips:
            route = tram_trip["route"]
            assert route
            assert isinstance(route, str)

            trip_head_sign = tram_trip["trip_head_sign"]
            assert trip_head_sign
            assert isinstance(trip_head_sign, str)

            stops = tram_trip["stops"]
            assert stops
            assert isinstance(stops, list)

            for stop in stops:
                stop_node_id = stop["id"]
                assert stop_node_id
                assert isinstance(stop_node_id, int)

                stop_time = stop["time"]
                assert stop_time >= 0
                assert isinstance(stop_time, int)

    def test_get_city_data_unknown_city_id(self):
        # Act
        response = self.client.get("/cities/1234567890")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "City not found"
