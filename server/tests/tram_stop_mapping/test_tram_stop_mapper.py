import json
import pickle
from pathlib import Path

import overpy
import pytest
from src.model import CityConfiguration, GTFSPackage
from src.tram_stop_mapper import TramStopMapper
from src.tram_stop_mapper.exceptions import TramStopMappingBuildError

TRAM_STOP_MAPPING_DIRECTORY = Path(__file__).parents[1] / "assets" / "tram_stop_mapping"


class TestTramStopMapper:
    def _get_tram_stop_mapping_test_data(self, source_directory: Path):
        with open(source_directory / "city_configuration.pickle", "rb") as file:
            city_configuration: CityConfiguration = pickle.load(file)

        with open(source_directory / "gtfs_package.pickle", "rb") as file:
            gtfs_package: GTFSPackage = pickle.load(file)

        with open(source_directory / "osm_relations_and_stops.pickle", "rb") as file:
            osm_relations_and_stops: overpy.Result = pickle.load(file)

        return (
            city_configuration,
            gtfs_package,
            osm_relations_and_stops,
        )

    def _get_expected_tram_stop_mapping(self, source_directory: Path):
        with open(
            source_directory / "expected_gtfs_stop_id_to_osm_node_id_mapping.json"
        ) as file:
            expected_gtfs_stop_id_to_osm_node_id_mapping: dict[str, int] = json.load(
                file
            )

        with open(
            source_directory / "expected_first_gtfs_stop_id_to_osm_node_id_mapping.json"
        ) as file:
            expected_first_gtfs_stop_id_to_osm_node_id_mapping: dict[str, list[int]] = (
                json.load(file)
            )

        with open(
            source_directory / "expected_last_gtfs_stop_id_to_osm_node_id_mapping.json"
        ) as file:
            expected_last_gtfs_stop_id_to_osm_node_id_mapping: dict[str, list[int]] = (
                json.load(file)
            )

        return (
            expected_gtfs_stop_id_to_osm_node_id_mapping,
            expected_first_gtfs_stop_id_to_osm_node_id_mapping,
            expected_last_gtfs_stop_id_to_osm_node_id_mapping,
        )

    def _get_expected_error_message(self, source_directory: Path):
        with open(source_directory / "expected_error_message.txt") as file:
            expected_error_message = file.read()

        return expected_error_message

    @pytest.mark.parametrize(
        "directory_name",
        [
            "2025-03-01T20:02:24",
        ],
    )
    def test_tram_stop_mapper(self, directory_name: str):
        # Arrange
        source_directory = TRAM_STOP_MAPPING_DIRECTORY / directory_name

        (
            city_configuration,
            gtfs_package,
            osm_relations_and_stops,
        ) = self._get_tram_stop_mapping_test_data(source_directory)

        (
            expected_gtfs_stop_id_to_osm_node_id_mapping,
            expected_first_gtfs_stop_id_to_osm_node_id_mapping,
            expected_last_gtfs_stop_id_to_osm_node_id_mapping,
        ) = self._get_expected_tram_stop_mapping(source_directory)

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
        "directory_name",
        [
            "2025-03-02T21:34:51",
            "2025-03-02T22:06:42",
            "2025-03-03T08:31:48",
        ],
    )
    def test_tram_stop_mapper_exception(self, directory_name: str):
        # Arrange
        source_directory = TRAM_STOP_MAPPING_DIRECTORY / directory_name

        (
            city_configuration,
            gtfs_package,
            osm_relations_and_stops,
        ) = self._get_tram_stop_mapping_test_data(source_directory)

        expected_error_message = self._get_expected_error_message(source_directory)

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(city_configuration, gtfs_package, osm_relations_and_stops)

        # Assert
        assert str(exc_info.value) == expected_error_message.strip()
