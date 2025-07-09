import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from pydantic import ValidationError
from pytest import LogCaptureFixture

from src.city_data_builder import CityConfiguration


class TestCityConfiguration:
    def _create_city_configurations(
        self,
        directory_path: Path,
        city_configuration: CityConfiguration,
        city_number: int,
    ):
        city_path = directory_path / f"city_{city_number}"
        city_path.mkdir()

        city_2021_path = city_path / f"2021-0{city_number + 1}-01.json"
        city_2021_path.touch()

        city_configuration.osm_area_name = f"city_{city_number}_{city_2021_path.name}"
        city_2021_path.write_text(city_configuration.model_dump_json())

        city_2023_path = city_path / f"2023-0{city_number + 1}-01.json"
        city_2023_path.touch()

        city_configuration.osm_area_name = f"city_{city_number}_{city_2023_path.name}"
        city_2023_path.write_text(city_configuration.model_dump_json())

        city_2025_path = city_path / f"2025-0{city_number + 1}-01.json"
        city_2025_path.touch()

        city_configuration.osm_area_name = f"city_{city_number}_{city_2025_path.name}"
        city_2025_path.write_text(city_configuration.model_dump_json())

    @pytest.fixture
    def config_directory_path(self, krakow_city_configuration: CityConfiguration):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory_path = Path(temporary_directory)

            for city_number in range(3):
                self._create_city_configurations(
                    directory_path,
                    krakow_city_configuration.model_copy(),
                    city_number,
                )

            yield directory_path

    def test_from_path(self, krakow_city_configuration: CityConfiguration):
        # Arrange
        path = Path.cwd() / "tests" / "assets" / "krakow_city_configuration.json"

        # Act
        city_configuration = CityConfiguration.from_path(path)

        # Assert
        assert isinstance(city_configuration, CityConfiguration)
        assert city_configuration == krakow_city_configuration

    def test_from_path_invalid_json(self, caplog: LogCaptureFixture):
        # Arrange
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"{Malformed json")
            path = Path.cwd() / temp_file.name

            # Act
            with pytest.raises(ValidationError) as exc_info, caplog.at_level(
                logging.ERROR, "src.city_data_builder.city_configuration"
            ):
                CityConfiguration.from_path(path)

            # Assert
            assert "Invalid JSON" in str(exc_info.value)
            assert f"Invalid configuration file: {path}" in caplog.text

    @patch.object(CityConfiguration, "CITIES_DIRECTORY_PATH", new_callable=PropertyMock)
    def test_get_all(
        self,
        mock_cities_directory_path: MagicMock,
        krakow_city_configuration: CityConfiguration,
        config_directory_path: Path,
    ):
        # Arrange
        mock_cities_directory_path.return_value = config_directory_path

        # Act
        city_configurations_by_id = CityConfiguration.get_all()

        # Assert
        for city_number in range(3):
            assert f"city_{city_number}" in city_configurations_by_id

            krakow_city_configuration.osm_area_name = (
                f"city_{city_number}_2025-0{city_number + 1}-01.json"
            )
            assert (
                city_configurations_by_id[f"city_{city_number}"]
                == krakow_city_configuration
            )

    @patch.object(CityConfiguration, "CITIES_DIRECTORY_PATH", new_callable=PropertyMock)
    def test_get_by_city_id(
        self,
        mock_cities_directory_path: MagicMock,
        krakow_city_configuration: CityConfiguration,
        config_directory_path: Path,
    ):
        # Arrange
        mock_cities_directory_path.return_value = config_directory_path
        krakow_city_configuration.osm_area_name = "city_1_2025-02-01.json"

        # Act
        city_configuration = CityConfiguration.get_by_city_id("city_1")

        # Assert
        assert city_configuration == krakow_city_configuration

    @patch.object(CityConfiguration, "CITIES_DIRECTORY_PATH", new_callable=PropertyMock)
    def test_get_by_city_id_unknown_city(
        self,
        mock_cities_directory_path: MagicMock,
        config_directory_path: Path,
    ):
        # Arrange
        mock_cities_directory_path.return_value = config_directory_path

        # Act
        city_configuration = CityConfiguration.get_by_city_id("city_4")

        # Assert
        assert city_configuration is None
