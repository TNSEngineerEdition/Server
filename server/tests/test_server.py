import logging
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from src.server import app


class TestServer:
    client = TestClient(app)

    def test_cities(self):
        response = self.client.get("/cities")
        cities = response.json()

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
                isinstance(osm_node_id, int)
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
        with caplog.at_level(logging.ERROR, logger="src.server"):
            response = self.client.get("/cities")

        assert response.status_code == 500
        assert response.json()["detail"] == "Invalid configuration files"

        assert "Invalid configuration file: " in caplog.text
        assert "ValidationError" in caplog.text
