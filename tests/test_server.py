import logging
import urllib.parse
from typing import Any
from unittest.mock import MagicMock, patch

import overpy
import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time
from pydantic import ValidationError

from city_data_builder import CityConfiguration, ResponseCityData
from server import app
from tram_stop_mapper import GTFSPackage, Weekday


class TestServer:
    client = TestClient(app)

    @patch("city_data_builder.city_configuration.CityConfiguration.get_all")
    def test_cities(
        self, get_all_mock: MagicMock, krakow_city_configuration: CityConfiguration
    ) -> None:
        # Arrange
        get_all_mock.return_value = {"krakow": krakow_city_configuration.model_dump()}

        # Act
        response = self.client.get("/cities")
        cities = response.json()

        # Assert
        assert response.status_code == 200
        assert isinstance(cities, dict)
        assert len(cities) == 1
        assert "krakow" in cities

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

    @patch("city_data_builder.city_configuration.CityConfiguration.get_all")
    def test_cities_validation_error(self, get_all_mock: MagicMock) -> None:
        # Arrange
        get_all_mock.side_effect = ValidationError.from_exception_data("", [])

        # Act
        response = self.client.get("/cities")

        # Assert
        assert response.status_code == 500
        assert response.json()["detail"] == "Invalid configuration files"

    def _assert_city_data_content(self, city_data: Any) -> None:
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
            assert isinstance(neighbors, dict)
            for key, neighbor in neighbors.items():
                assert isinstance(key, str)
                assert isinstance(neighbor, dict)

                neighbor_id = neighbor["id"]
                assert neighbor_id
                assert isinstance(neighbor_id, int)
                assert int(key) == neighbor_id

                neighbor_distance = neighbor["distance"]
                assert neighbor_distance
                assert isinstance(neighbor_distance, float)

                neighbor_azimuth = neighbor["azimuth"]
                assert isinstance(neighbor_azimuth, float)
                assert -180 <= neighbor_azimuth <= 180

                neighbor_max_speed = neighbor["max_speed"]
                assert isinstance(neighbor_max_speed, float)
                assert neighbor_max_speed > 0

            if "name" in tram_track_node or "gtfs_stop_ids" in tram_track_node:
                assert isinstance(tram_track_node["name"], str)

                gtfs_stop_ids = tram_track_node["gtfs_stop_ids"]
                assert isinstance(gtfs_stop_ids, list)
                assert all(isinstance(item, str) for item in gtfs_stop_ids)

        assert any(
            ("name" in tram_track_node or "gtfs_stop_ids" in tram_track_node)
            for tram_track_node in tram_track_graph
        )

        tram_routes = city_data["tram_routes"]
        assert tram_routes
        assert isinstance(tram_routes, list)

        for tram_route in tram_routes:
            route = tram_route["name"]
            assert route
            assert isinstance(route, str)

            background_color = tram_route["background_color"]
            assert background_color
            assert isinstance(background_color, str)
            assert len(background_color) == 6

            text_color = tram_route["text_color"]
            assert text_color
            assert isinstance(text_color, str)
            assert len(text_color) == 6

            trips = tram_route["trips"]
            assert isinstance(trips, list)
            for trip in trips:
                trip_head_sign = trip["trip_head_sign"]
                assert trip_head_sign
                assert isinstance(trip_head_sign, str)

                stops = trip["stops"]
                assert stops
                assert isinstance(stops, list)

                for stop in stops:
                    stop_node_id = stop["id"]
                    assert stop_node_id
                    assert isinstance(stop_node_id, int)

                    stop_time = stop["time"]
                    assert stop_time >= 0
                    assert isinstance(stop_time, int)

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.is_fresh", return_value=False)
    def test_get_city_data(
        self,
        cache_is_fresh_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        krakow_city_configuration: CityConfiguration,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 200
        self._assert_city_data_content(response.json())

        cache_is_fresh_mock.assert_called_once_with("krakow", Weekday.WEDNESDAY)
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with("Kraków")
        gtfs_package_from_url_mock.assert_called_once_with(
            "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip"
        )
        get_by_city_id_mock.assert_called_once_with("krakow")

    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.is_fresh", return_value=False)
    def test_get_city_data_with_weekday(
        self,
        cache_is_fresh_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        krakow_city_configuration: CityConfiguration,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        response = self.client.get("/cities/krakow", params={"weekday": "monday"})

        # Assert
        assert response.status_code == 200
        self._assert_city_data_content(response.json())

        cache_is_fresh_mock.assert_called_once_with("krakow", Weekday.MONDAY)
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with("Kraków")
        gtfs_package_from_url_mock.assert_called_once_with(
            "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip"
        )
        get_by_city_id_mock.assert_called_once_with("krakow")

    def test_get_city_data_unknown_city_id(self) -> None:
        # Act
        response = self.client.get("/cities/1234567890")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "City not found"

    def test_get_city_data_invalid_weekday(self) -> None:
        # Arrange
        expected_response_detail = (
            "Invalid weekday: 1234567890. Must be one of: "
            "['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']"
        )

        # Act
        response = self.client.get("/cities/krakow", params={"weekday": "1234567890"})

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == expected_response_detail

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.is_fresh", return_value=False)
    @patch("city_data_cache.CityDataCache.get")
    def test_get_city_data_exception_during_data_build(
        self,
        cache_get_mock: MagicMock,
        cache_is_fresh_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        krakow_response_city_data: ResponseCityData,
        krakow_city_configuration: CityConfiguration,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        expected_log_message = (
            "Failed to build city data for city krakow and weekday wednesday"
        )

        cache_get_mock.return_value = krakow_response_city_data
        get_relations_and_stops_mock.side_effect = Exception("Error")
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        with caplog.at_level(logging.ERROR, "server"):
            response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 200
        assert expected_log_message in caplog.text

        self._assert_city_data_content(response.json())

        cache_get_mock.assert_called_once_with("krakow", Weekday.WEDNESDAY)
        cache_is_fresh_mock.assert_called_once_with("krakow", Weekday.WEDNESDAY)
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_by_city_id_mock.assert_called_once_with("krakow")

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.is_fresh", return_value=False)
    @patch("city_data_cache.CityDataCache.get")
    def test_get_city_data_exception_during_data_build_empty_cache(
        self,
        cache_get_mock: MagicMock,
        cache_is_fresh_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        expected_log_message = (
            "Failed to build city data for city krakow and weekday wednesday"
        )

        cache_get_mock.return_value = None
        get_relations_and_stops_mock.side_effect = Exception("Error")
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        with caplog.at_level(logging.ERROR, "server"):
            response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 500
        assert expected_log_message in caplog.text
        assert response.json()["detail"] == "Data processing for krakow failed"

        cache_get_mock.assert_called_once_with("krakow", Weekday.WEDNESDAY)
        cache_is_fresh_mock.assert_called_once_with("krakow", Weekday.WEDNESDAY)
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_by_city_id_mock.assert_called_once_with("krakow")
