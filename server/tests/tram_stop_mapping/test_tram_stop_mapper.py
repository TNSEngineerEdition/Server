import json
import pickle
from pathlib import Path
from zipfile import ZipFile

import overpy
import pytest
from src.model import CityConfiguration, GTFSPackage
from src.tram_stop_mapper import TramStopMapper
from src.tram_stop_mapper.exceptions import TramStopMappingBuildError

TRAM_STOP_MAPPING_DIRECTORY = Path(__file__).parents[1] / "assets" / "tram_stop_mapping"


class TestTramStopMapper:
    def _get_tram_stop_mapping_test_data(self, zip_file: ZipFile):
        with zip_file.open("city_configuration.pickle") as file:
            city_configuration: CityConfiguration = pickle.load(file)

        with zip_file.open("gtfs_package.pickle") as file:
            gtfs_package: GTFSPackage = pickle.load(file)

        with zip_file.open("osm_relations_and_stops.pickle") as file:
            osm_relations_and_stops: overpy.Result = pickle.load(file)

        return (
            city_configuration,
            gtfs_package,
            osm_relations_and_stops,
        )

    def _get_expected_tram_stop_mapping(self, zip_file: ZipFile):
        with zip_file.open("expected_gtfs_stop_id_to_osm_node_id_mapping.json") as file:
            expected_gtfs_stop_id_to_osm_node_id_mapping: dict[str, int] = json.load(
                file
            )

        with zip_file.open(
            "expected_first_gtfs_stop_id_to_osm_node_id_mapping.json"
        ) as file:
            expected_first_gtfs_stop_id_to_osm_node_id_mapping: dict[str, list[int]] = (
                json.load(file)
            )

        with zip_file.open(
            "expected_last_gtfs_stop_id_to_osm_node_id_mapping.json"
        ) as file:
            expected_last_gtfs_stop_id_to_osm_node_id_mapping: dict[str, list[int]] = (
                json.load(file)
            )

        return (
            expected_gtfs_stop_id_to_osm_node_id_mapping,
            expected_first_gtfs_stop_id_to_osm_node_id_mapping,
            expected_last_gtfs_stop_id_to_osm_node_id_mapping,
        )

    def _get_expected_error_message(self, zip_file: ZipFile):
        with zip_file.open("expected_error_message.txt") as file:
            expected_error_message = file.read().decode()

        return expected_error_message

    @pytest.mark.parametrize(
        "file_name",
        [
            "2025-03-01T20:02:24.zip",
        ],
    )
    def test_tram_stop_mapper(self, file_name: str):
        # Arrange
        with ZipFile(TRAM_STOP_MAPPING_DIRECTORY / file_name) as zip_file:
            (
                city_configuration,
                gtfs_package,
                osm_relations_and_stops,
            ) = self._get_tram_stop_mapping_test_data(zip_file)

            (
                expected_gtfs_stop_id_to_osm_node_id_mapping,
                expected_first_gtfs_stop_id_to_osm_node_id_mapping,
                expected_last_gtfs_stop_id_to_osm_node_id_mapping,
            ) = self._get_expected_tram_stop_mapping(zip_file)

        # Act
        tram_stop_mapper = TramStopMapper(
            city_configuration, gtfs_package, osm_relations_and_stops
        )

        # Assert
        assert (
            tram_stop_mapper.gtfs_stop_id_to_osm_node_id_mapping
            == expected_gtfs_stop_id_to_osm_node_id_mapping
        )

        assert (
            tram_stop_mapper.first_gtfs_stop_id_to_osm_node_ids
            == expected_first_gtfs_stop_id_to_osm_node_id_mapping
        )

        assert (
            tram_stop_mapper.last_gtfs_stop_id_to_osm_node_ids
            == expected_last_gtfs_stop_id_to_osm_node_id_mapping
        )

    @pytest.mark.parametrize(
        "file_name",
        [
            "2025-03-02T21:34:51.zip",
            "2025-03-02T22:06:42.zip",
            "2025-03-03T08:31:48.zip",
        ],
    )
    def test_tram_stop_mapper_exception(self, file_name: str):
        # Arrange
        with ZipFile(TRAM_STOP_MAPPING_DIRECTORY / file_name) as zip_file:
            (
                city_configuration,
                gtfs_package,
                osm_relations_and_stops,
            ) = self._get_tram_stop_mapping_test_data(zip_file)

            expected_error_message = self._get_expected_error_message(zip_file)

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(city_configuration, gtfs_package, osm_relations_and_stops)

        # Assert
        assert str(exc_info.value) == expected_error_message.strip()
