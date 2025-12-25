import datetime
import io
import logging
import urllib.parse
from typing import Any, IO
from unittest.mock import MagicMock, patch

import overpy
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time
from pydantic import ValidationError

from city_data_builder import CityConfiguration, ResponseCityData
from server import app
from tram_stop_mapper import (
    GTFSPackage,
    TramStopMappingBuildError,
    TramStopMappingErrors,
)


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

        for city_id, payload in cities.items():
            assert city_id
            assert isinstance(city_id, str)

            configuration = payload["city_configuration"]
            available_dates = payload["available_dates"]

            osm_area_name = configuration["osm_area_name"]
            assert osm_area_name
            assert isinstance(osm_area_name, str)

            gtfs_url = configuration["gtfs_url"]
            assert gtfs_url
            assert isinstance(gtfs_url, str)

            url_parse_result = urllib.parse.urlparse(gtfs_url)
            assert url_parse_result.scheme
            assert url_parse_result.netloc

            ignored_gtfs_lines = configuration["ignored_gtfs_lines"]
            assert isinstance(ignored_gtfs_lines, list)
            assert all(isinstance(line, str) for line in ignored_gtfs_lines)
            assert len(set(ignored_gtfs_lines)) == len(ignored_gtfs_lines)

            custom_stop_mapping = configuration["custom_stop_mapping"]
            assert isinstance(custom_stop_mapping, dict)
            assert all(
                isinstance(gtfs_stop_id, str) for gtfs_stop_id in custom_stop_mapping
            )
            assert all(
                isinstance(osm_node_id, (int, list))
                for osm_node_id in custom_stop_mapping.values()
            )

            assert isinstance(available_dates, list)
            assert all(isinstance(d, str) for d in available_dates)

            parsed_dates = [datetime.date.fromisoformat(d) for d in available_dates]
            assert all(isinstance(d, datetime.date) for d in parsed_dates)
            assert parsed_dates == sorted(parsed_dates, reverse=True)

        assert any(configuration["osm_area_name"] == "Kraków" for _ in cities.values())

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

            variants = tram_route["variants"]
            assert isinstance(variants, dict)

            trips = tram_route["trips"]
            assert isinstance(trips, list)
            for trip in trips:
                trip_head_sign = trip["trip_head_sign"]
                assert trip_head_sign
                assert isinstance(trip_head_sign, str)

                variant = trip["variant"]
                assert variant is None or variant in variants

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
    @patch("city_data_cache.CityDataCache.get", return_value=None)
    @patch("city_data_cache.CityDataCache.store", return_value=None)
    def test_get_city_data(
        self,
        cache_store_mock: MagicMock,
        cache_get_mock: MagicMock,
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

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())
        cache_store_mock.assert_called_once_with(
            "krakow",
            datetime.date.today(),
            ResponseCityData.model_validate(response.json()),
        )

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.get", return_value=None)
    @patch("city_data_cache.CityDataCache.store", return_value=None)
    def test_get_city_data_from_cache(
        self,
        cache_store_mock: MagicMock,
        cache_get_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        krakow_city_configuration: CityConfiguration,
        krakow_response_city_data: ResponseCityData,
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
        cache_get_mock.return_value = krakow_response_city_data

        # Act
        response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 200
        self._assert_city_data_content(response.json())

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())
        cache_store_mock.assert_not_called()

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("city_data_builder.city_data_builder.CityDataBuilder.__init__")
    @patch("city_data_cache.CityDataCache.get", return_value=None)
    def test_get_city_data_tram_stop_mapping_error(
        self,
        cache_get_mock: MagicMock,
        city_data_builder_init_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
    ) -> None:
        # Arrange
        get_by_city_id_mock.return_value = krakow_city_configuration
        city_data_builder_init_mock.side_effect = TramStopMappingBuildError(
            TramStopMappingErrors(missing_relations_for_lines={"10"})
        )

        # Act
        response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 500
        assert response.json()["detail"] == (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            "Missing relations for lines: 10"
        )

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())

    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.get")
    def test_get_city_data_with_weekday(
        self,
        cache_get_mock: MagicMock,
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

        get_by_city_id_mock.assert_called_once_with("krakow")
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [
                1770194211,
                2163355814,
                10020926691,
                2163355821,
                2375524420,
                629106153,
            ],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with("Kraków")
        gtfs_package_from_url_mock.assert_called_once_with(
            "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip"
        )
        cache_get_mock.assert_not_called()

    @patch("server.CityDataCache.get")
    def test_get_city_data_with_date(
        self,
        cache_get_mock: MagicMock,
        krakow_response_city_data: ResponseCityData,
    ) -> None:
        # Arrange
        cache_get_mock.return_value = krakow_response_city_data

        # Act
        response = self.client.get("/cities/krakow", params={"date": "2025-01-01"})

        # Assert
        assert response.status_code == 200
        self._assert_city_data_content(response.json())

        cache_get_mock.assert_called_once_with("krakow", datetime.date(2025, 1, 1))

    def test_get_city_data_unknown_city_id(self) -> None:
        # Act
        response = self.client.get("/cities/1234567890")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "City 1234567890 not found"

    def test_get_city_data_invalid_weekday(self) -> None:
        # Arrange
        expected_response_detail = [
            {
                "type": "enum",
                "loc": ["query", "weekday"],
                "msg": "Input should be 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday' or 'sunday'",
                "input": "1234567890",
                "ctx": {
                    "expected": "'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday' or 'sunday'"
                },
            }
        ]

        # Act
        response = self.client.get("/cities/krakow", params={"weekday": "1234567890"})

        # Assert
        assert response.status_code == 422
        assert response.json()["detail"] == expected_response_detail

    def test_get_city_data_invalid_date(self) -> None:
        # Arrange
        expected_response_detail = [
            {
                "type": "date_from_datetime_parsing",
                "loc": ["query", "date"],
                "msg": "Input should be a valid date or datetime, month value is outside expected range of 1-12",
                "input": "2025-13-13",
                "ctx": {"error": "month value is outside expected range of 1-12"},
            }
        ]

        # Act
        response = self.client.get("/cities/krakow", params={"date": "2025-13-13"})

        # Assert
        assert response.status_code == 422
        assert response.json()["detail"] == expected_response_detail

    def test_get_city_data_missing_date(self) -> None:
        # Arrange
        expected_response_detail = (
            "City data for krakow not found in cache for 2025-12-10"
        )

        # Act
        response = self.client.get("/cities/krakow", params={"date": "2025-12-10"})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == expected_response_detail

    def test_get_city_data_both_params(self) -> None:
        # Arrange
        expected_response_detail = "Provide either date or weekday"

        # Act
        response = self.client.get(
            "/cities/krakow", params={"date": "2025-09-15", "weekday": "monday"}
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == expected_response_detail

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.get")
    def test_get_city_data_exception_during_data_build_empty_cache(
        self,
        cache_get_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        expected_log_message = (
            "Failed to build city data for city krakow for weekday wednesday"
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

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_by_city_id_mock.assert_called_once_with("krakow")

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.get_trips_for_service_ids")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.get", return_value=None)
    def test_get_city_data_exception_during_response_build_empty_cache(
        self,
        cache_get_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_get_trips_for_service_ids_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        krakow_city_configuration: CityConfiguration,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        expected_log_message = (
            "Failed to build response data for city krakow for weekday wednesday"
        )

        cache_get_mock.return_value = None
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_get_trips_for_service_ids_mock.side_effect = Exception("Error")
        gtfs_package_from_url_mock.return_value = gtfs_package
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        with caplog.at_level(logging.ERROR, "server"):
            response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 500
        assert expected_log_message in caplog.text
        assert response.json()["detail"] == "Data processing for krakow failed"

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())
        get_by_city_id_mock.assert_called_once_with("krakow")
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [
                1770194211,
                2163355814,
                10020926691,
                2163355821,
                2375524420,
                629106153,
            ],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with("Kraków")
        gtfs_package_from_url_mock.assert_called_once_with(
            "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip"
        )

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    @patch("city_data_cache.CityDataCache.get")
    def test_get_city_data_overpass_gateway_timeout_empty_cache(
        self,
        cache_get_mock: MagicMock,
        get_relations_and_stops_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
    ) -> None:
        # Arrange
        cache_get_mock.return_value = None
        get_relations_and_stops_mock.side_effect = (
            overpy.exception.OverpassGatewayTimeout()
        )
        get_by_city_id_mock.return_value = krakow_city_configuration

        # Act
        response = self.client.get("/cities/krakow")

        # Assert
        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "Overpass gateway timeout: Server load too high"
        )

        cache_get_mock.assert_called_once_with("krakow", datetime.date.today())
        get_relations_and_stops_mock.assert_called_once_with(
            "Kraków",
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_by_city_id_mock.assert_called_once_with("krakow")

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_get_city_data_with_custom_schedule(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        custom_gtfs_package_byte_buffer: IO[bytes],
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
        response = self.client.post(
            "/cities/krakow",
            files={
                "custom_schedule_file": (
                    "custom_schedule.zip",
                    custom_gtfs_package_byte_buffer,
                    "application/zip",
                )
            },
        )

        # Assert
        assert response.status_code == 200

        response_data = response.json()
        self._assert_city_data_content(response_data)

        assert all(item["name"] != "52" for item in response_data["tram_routes"])

    def test_get_city_data_with_custom_schedule_invalid_content_type(
        self, custom_gtfs_package_byte_buffer: IO[bytes]
    ) -> None:
        # Act
        response = self.client.post(
            "/cities/krakow",
            files={
                "custom_schedule_file": (
                    "custom_schedule.zip",
                    custom_gtfs_package_byte_buffer,
                    "application/octet-stream",
                )
            },
        )

        # Assert
        assert response.status_code == 400
        assert response.json() == {"detail": "Custom schedule file must be a ZIP file"}

    def test_get_city_data_with_custom_schedule_invalid_file(self) -> None:
        # Act
        response = self.client.post(
            "/cities/krakow",
            files={
                "custom_schedule_file": (
                    "custom_schedule.zip",
                    b"1234567890987654321",
                    "application/zip",
                )
            },
        )

        # Assert
        assert response.status_code == 422
        assert response.json() == {"detail": "File is not a ZIP file"}

    def test_get_city_data_with_custom_schedule_invalid_file_checksum(
        self, custom_gtfs_package_byte_buffer: IO[bytes]
    ) -> None:
        # Arrange
        buffer_bytearray = bytearray(custom_gtfs_package_byte_buffer.read())
        buffer_bytearray[125] ^= 0xFF
        modified_custom_schedule = bytes(buffer_bytearray)

        # Act
        response = self.client.post(
            "/cities/krakow",
            files={
                "custom_schedule_file": (
                    "custom_schedule.zip",
                    modified_custom_schedule,
                    "application/zip",
                )
            },
        )

        # Assert
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid file: stops.txt"}

    @pytest.mark.parametrize("excluded_file_name", GTFSPackage.FILE_NAMES)
    def test_get_city_data_with_custom_schedule_missing_file(
        self,
        gtfs_package_byte_buffer_selected_files: io.BytesIO,
        excluded_file_name: str,
    ) -> None:
        # Act
        response = self.client.post(
            "/cities/krakow",
            files={
                "custom_schedule_file": (
                    "custom_schedule.zip",
                    gtfs_package_byte_buffer_selected_files,
                    "application/zip",
                )
            },
        )

        # Assert
        assert response.status_code == 422
        assert response.json() == {
            "detail": f"\"There is no item named '{excluded_file_name}' in the archive\""
        }

    @freeze_time("2025-01-01")
    @patch("city_data_builder.city_configuration.CityConfiguration.get_by_city_id")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_get_city_data_with_custom_schedule_unknown_stop(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        get_by_city_id_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        custom_gtfs_package: GTFSPackage,
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

        custom_gtfs_package.stop_times = pd.concat(
            [
                custom_gtfs_package.stop_times,
                pd.DataFrame(
                    [
                        [
                            "block_393_trip_1_service_1",
                            "05:06:00",
                            "05:06:00",
                            "stop_000_00000",
                            26,
                            "",
                            1,
                            0,
                            0.3,
                            1,
                        ]
                    ],
                    columns=custom_gtfs_package.stop_times.columns,
                ),
            ]
        )

        with io.BytesIO() as buffer:
            custom_gtfs_package.to_zip_file(buffer)
            buffer.seek(0)

            # Act
            response = self.client.post(
                "/cities/krakow",
                files={
                    "custom_schedule_file": (
                        "custom_schedule.zip",
                        buffer,
                        "application/zip",
                    )
                },
            )

        # Assert
        assert response.status_code == 500
        assert response.json() == {
            "detail": "Stop stop_000_00000 not found in any mapping."
        }
