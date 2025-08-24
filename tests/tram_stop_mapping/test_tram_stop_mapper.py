import json
from collections.abc import Hashable
from zipfile import ZipFile

import overpy
import pytest

from city_data_builder import CityConfiguration
from tram_stop_mapper import (
    GTFSPackage,
    TramStopMapper,
    TramStopMappingBuildError,
)


class TestTramStopMapper:
    @pytest.fixture
    def tram_stop_mapping(self):
        with ZipFile("tests/assets/tram_stop_mapping.zip") as zip_file:
            with zip_file.open(
                "expected_gtfs_stop_id_to_osm_node_id_mapping.json"
            ) as file:
                single_mapping: dict[str, int] = json.load(file)

            with zip_file.open(
                "expected_first_gtfs_stop_id_to_osm_node_id_mapping.json"
            ) as file:
                first_mapping: dict[str, list[int]] = json.load(file)

            with zip_file.open(
                "expected_last_gtfs_stop_id_to_osm_node_id_mapping.json"
            ) as file:
                last_mapping: dict[str, list[int]] = json.load(file)

        return single_mapping, first_mapping, last_mapping

    def test_tram_stop_mapper(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stop_mapping: tuple[
            dict[str, int], dict[str, list[int]], dict[str, list[int]]
        ],
    ):
        # Act
        tram_stop_mapper = TramStopMapper(
            krakow_city_configuration,
            gtfs_package,
            relations_and_stops_overpass_query_result,
        )

        # Assert
        assert (
            tram_stop_mapper.gtfs_stop_id_to_osm_node_id_mapping == tram_stop_mapping[0]
        )

        assert (
            tram_stop_mapper.first_gtfs_stop_id_to_osm_node_ids == tram_stop_mapping[1]
        )

        assert (
            tram_stop_mapper.last_gtfs_stop_id_to_osm_node_ids == tram_stop_mapping[2]
        )

    def test_tram_stop_mapper_missing_relations_for_lines_exception(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        gtfs_package.routes.loc["route_12345"] = [
            "agency_1",
            12345,
            12345,
            None,
            900,
            None,
            "B60000",
            "FFFFFF",
        ]
        gtfs_package.trips.loc["block_12345_trip_12345_service_12345"] = [
            "route_12345",
            "service_4",
            "Some stop",
            None,
            1,
            "block_5",
            "shape_23347",
            0,
        ]

        expected_exception_message = (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            "Missing relations for lines: 12345"
        )

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(
                krakow_city_configuration,
                gtfs_package,
                relations_and_stops_overpass_query_result,
            )

        # Assert
        assert str(exc_info.value) == expected_exception_message

    def test_tram_stop_mapper_nodes_with_conflict_exception(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        krakow_city_configuration.custom_stop_mapping["stop_386_285919"] = 2419732952

        expected_exception_message = (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            "Nodes with conflict:\n"
            "stop_386_285919: Salwator 01 (2419732952), Teatr Variété 01 (2426058893)"
        )

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(
                krakow_city_configuration,
                gtfs_package,
                relations_and_stops_overpass_query_result,
            )

        # Assert
        assert str(exc_info.value) == expected_exception_message

    def test_tram_stop_mapper_stops_without_mapping_exception(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        gtfs_package.stops.loc["stop_12345_12345"] = [
            None,
            "Grodzki Urząd Pracy",
            None,
            50,
            20,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
        ]

        expected_exception_message = (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            "Stops without mapping: stop_12345_12345"
        )

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(
                krakow_city_configuration,
                gtfs_package,
                relations_and_stops_overpass_query_result,
            )

        # Assert
        assert str(exc_info.value) == expected_exception_message

    def test_tram_stop_mapper_underutilized_relations_exception(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        gtfs_package.routes.drop("route_698", inplace=True)

        expected_exception_message_start = (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            "Underutilized relations:\n"
        )

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(
                krakow_city_configuration,
                gtfs_package,
                relations_and_stops_overpass_query_result,
            )

        # Assert
        exception_message = str(exc_info.value)

        assert exception_message.startswith(expected_exception_message_start)
        assert "Relation ID: 968203" in exception_message
        assert "Relation ID: 3155965" in exception_message

    def test_tram_stop_mapper_all_exceptions(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        krakow_city_configuration.custom_stop_mapping["stop_386_285919"] = 2419732952

        gtfs_package.routes.loc["route_12345"] = [
            "agency_1",
            12345,
            12345,
            None,
            900,
            None,
            "B60000",
            "FFFFFF",
        ]
        gtfs_package.routes.drop("route_698", inplace=True)

        gtfs_package.trips.loc["block_12345_trip_12345_service_12345"] = [
            "route_12345",
            "service_4",
            "Some stop",
            None,
            1,
            "block_5",
            "shape_23347",
            0,
        ]

        gtfs_package.stops.loc["stop_12345_12345"] = [
            None,
            "Grodzki Urząd Pracy",
            None,
            50,
            20,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
        ]

        expected_exception_message_start = (
            "Unable to build correct mapping of GTFS stops to OSM nodes.\n"
        )

        # Act
        with pytest.raises(TramStopMappingBuildError) as exc_info:
            TramStopMapper(
                krakow_city_configuration,
                gtfs_package,
                relations_and_stops_overpass_query_result,
            )

        # Assert
        exception_message = str(exc_info.value)

        assert exception_message.startswith(expected_exception_message_start)
        assert "Stops without mapping: " in exception_message
        assert "Nodes with conflict:\n" in exception_message
        assert "Missing relations for lines: " in exception_message
        assert "Underutilized relations:\n" in exception_message

    @staticmethod
    def _get_unique_trips_from_stop_nodes(stop_nodes: list[list[Hashable]]):
        return set(map(tuple, stop_nodes))

    def test_stop_nodes_by_gtfs_trip_id(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        expected_trip_stop_count = gtfs_package.stop_times.value_counts("trip_id")

        unique_trips_from_gtfs = self._get_unique_trips_from_stop_nodes(
            gtfs_package.stop_id_sequence_by_trip_id.values()
        )

        tram_stop_mapper = TramStopMapper(
            krakow_city_configuration,
            gtfs_package,
            relations_and_stops_overpass_query_result,
        )

        # Act
        stop_nodes_by_gtfs_trip_id = tram_stop_mapper.stop_nodes_by_gtfs_trip_id
        unique_trips = self._get_unique_trips_from_stop_nodes(
            stop_nodes_by_gtfs_trip_id.values()
        )

        # Assert
        assert set(stop_nodes_by_gtfs_trip_id.keys()) == set(gtfs_package.trips.index)

        # Since GTFS stop_id may map to multiple OSM node_ids, the count of
        # generated unique trips cannot be less than what's in the GTFS dataset
        assert len(unique_trips) >= len(unique_trips_from_gtfs)

        for gtfs_trip_id, expected_stop_count in expected_trip_stop_count.items():
            assert len(stop_nodes_by_gtfs_trip_id[gtfs_trip_id]) == expected_stop_count

    def test_stop_ids_by_node_id(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        tram_stop_mapper = TramStopMapper(
            krakow_city_configuration,
            gtfs_package,
            relations_and_stops_overpass_query_result,
        )

        # Act
        gtfs_stop_ids_by_node_id = tram_stop_mapper.gtfs_stop_ids_by_node_id

        # Assert
        assert all(
            gtfs_stop_id in gtfs_stop_ids_by_node_id[node_id]
            for (
                gtfs_stop_id,
                node_id,
            ) in tram_stop_mapper.gtfs_stop_id_to_osm_node_id_mapping.items()
        )

        assert all(
            gtfs_stop_id in gtfs_stop_ids_by_node_id[node_id]
            for (
                gtfs_stop_id,
                node_ids,
            ) in tram_stop_mapper.first_gtfs_stop_id_to_osm_node_ids.items()
            for node_id in node_ids
        )

        assert all(
            gtfs_stop_id in gtfs_stop_ids_by_node_id[node_id]
            for (
                gtfs_stop_id,
                node_ids,
            ) in tram_stop_mapper.last_gtfs_stop_id_to_osm_node_ids.items()
            for node_id in node_ids
        )

    def test_trip_stops_by_trip_id(
        self,
        krakow_city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        relations_and_stops_overpass_query_result: overpy.Result,
    ):
        # Arrange
        expected_trip_stop_count = gtfs_package.stop_times.value_counts("trip_id")

        tram_stop_mapper = TramStopMapper(
            krakow_city_configuration,
            gtfs_package,
            relations_and_stops_overpass_query_result,
        )

        # Act
        trip_stops_data = tram_stop_mapper.trip_stops_by_trip_id

        # Assert
        assert all(
            len(trip_stops_data[trip_id]) == expected_stop_count
            for trip_id, expected_stop_count in expected_trip_stop_count.items()
        )
