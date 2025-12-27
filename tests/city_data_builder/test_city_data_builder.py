from unittest.mock import MagicMock, patch

import numpy as np
import overpy
import pandas as pd
import pytest
from freezegun import freeze_time

from city_data_builder import CityConfiguration, CityDataBuilder, ResponseGraphTramStop
from tram_stop_mapper import GTFSPackage, TramStopNotFound, Weekday


class TestCityDataBuilder:
    def _assert_city_data_builder(
        self,
        city_data_builder: CityDataBuilder,
        expected_node_count: int,
        expected_edge_count: int,
        expected_route_count: int,
        expected_trip_count: int,
        expected_stop_count: int,
    ) -> None:
        assert len(city_data_builder.tram_track_graph_data) == expected_node_count
        assert (
            sum(len(node.neighbors) for node in city_data_builder.tram_track_graph_data)
            == expected_edge_count
        )

        assert len(city_data_builder.tram_routes_data) == expected_route_count

        trip_count = sum(
            len(route.trips) for route in city_data_builder.tram_routes_data
        )
        assert trip_count == expected_trip_count

        trip_stop_count = sum(
            len(trip.stops)
            for route in city_data_builder.tram_routes_data
            for trip in route.trips
        )
        assert trip_stop_count == expected_stop_count

        assert all(route.trips for route in city_data_builder.tram_routes_data)

        assert all(
            trip.stops
            for route in city_data_builder.tram_routes_data
            for trip in route.trips
        )

        nodes_by_id = {
            node.id: node for node in city_data_builder.tram_track_graph_data
        }

        assert all(
            isinstance(nodes_by_id[trip_stop.id], ResponseGraphTramStop)
            for route in city_data_builder.tram_routes_data
            for trip in route.trips
            for trip_stop in trip.stops
        )

    @pytest.mark.parametrize(
        (
            "weekday",
            "expected_route_count",
            "expected_trip_count",
            "expected_stop_count",
        ),
        [
            pytest.param(Weekday.MONDAY, 23, 4407, 115266, id=Weekday.MONDAY),
            pytest.param(Weekday.TUESDAY, 23, 4407, 115266, id=Weekday.TUESDAY),
            pytest.param(Weekday.WEDNESDAY, 23, 4407, 115266, id=Weekday.WEDNESDAY),
            pytest.param(Weekday.THURSDAY, 23, 4407, 115266, id=Weekday.THURSDAY),
            pytest.param(Weekday.FRIDAY, 26, 4497, 117602, id=Weekday.FRIDAY),
            pytest.param(Weekday.SATURDAY, 23, 2641, 70399, id=Weekday.SATURDAY),
            pytest.param(Weekday.SUNDAY, 23, 2375, 62988, id=Weekday.SUNDAY),
        ],
    )
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_city_data_builder(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        weekday: Weekday,
        expected_route_count: int,
        expected_trip_count: int,
        expected_stop_count: int,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package

        expected_node_count, expected_edge_count = 43321, 46047

        # Act
        city_data_builder = CityDataBuilder(
            krakow_city_configuration, weekday, is_today=False
        )

        # Assert
        self._assert_city_data_builder(
            city_data_builder,
            expected_node_count,
            expected_edge_count,
            expected_route_count,
            expected_trip_count,
            expected_stop_count,
        )

        get_relations_and_stops_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name,
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name
        )
        gtfs_package_from_url_mock.assert_called_once_with(
            krakow_city_configuration.gtfs_url
        )

    @freeze_time("2025-05-01")
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_city_data_builder_today(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package

        expected_node_count, expected_edge_count = 43321, 46047

        # Act
        city_data_builder = CityDataBuilder(
            krakow_city_configuration, Weekday.THURSDAY, is_today=True
        )

        # Assert
        # Although the weekday is Thursday, the schedule should be for Sunday
        self._assert_city_data_builder(
            city_data_builder,
            expected_node_count,
            expected_edge_count,
            expected_route_count=23,
            expected_trip_count=2375,
            expected_stop_count=62988,
        )

        get_relations_and_stops_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name,
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name
        )
        gtfs_package_from_url_mock.assert_called_once_with(
            krakow_city_configuration.gtfs_url
        )

    @pytest.mark.parametrize(
        (
            "weekday",
            "expected_route_count",
            "expected_trip_count",
            "expected_stop_count",
        ),
        [
            pytest.param(Weekday.MONDAY, 22, 4111, 105820, id=Weekday.MONDAY),
            pytest.param(Weekday.TUESDAY, 22, 4111, 105820, id=Weekday.TUESDAY),
            pytest.param(Weekday.WEDNESDAY, 22, 4111, 105820, id=Weekday.WEDNESDAY),
            pytest.param(Weekday.THURSDAY, 22, 4111, 105820, id=Weekday.THURSDAY),
            pytest.param(Weekday.FRIDAY, 25, 4197, 108111, id=Weekday.FRIDAY),
            pytest.param(Weekday.SATURDAY, 22, 2428, 63687, id=Weekday.SATURDAY),
            pytest.param(Weekday.SUNDAY, 22, 2198, 57536, id=Weekday.SUNDAY),
        ],
    )
    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_city_data_builder_with_custom_schedule(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        custom_gtfs_package: GTFSPackage,
        weekday: Weekday,
        expected_route_count: int,
        expected_trip_count: int,
        expected_stop_count: int,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package

        expected_node_count, expected_edge_count = 43321, 46047

        # Act
        city_data_builder = CityDataBuilder(
            krakow_city_configuration,
            weekday,
            is_today=False,
            custom_gtfs_package=custom_gtfs_package,
        )

        # Assert
        self._assert_city_data_builder(
            city_data_builder,
            expected_node_count,
            expected_edge_count,
            expected_route_count,
            expected_trip_count,
            expected_stop_count,
        )

        get_relations_and_stops_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name,
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name
        )
        gtfs_package_from_url_mock.assert_called_once_with(
            krakow_city_configuration.gtfs_url
        )

    @patch("tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("overpass_client.OverpassClient.get_relations_and_stops")
    def test_tram_routes_data_with_custom_schedule_stop_not_found_in_mapping(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        custom_gtfs_package: GTFSPackage,
    ) -> None:
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package

        custom_gtfs_package.stop_times = pd.concat(
            [
                custom_gtfs_package.stop_times,
                pd.DataFrame(
                    [
                        [
                            "block_4_trip_1_service_4",
                            "06:23:00",
                            "06:23:00",
                            "stop_000_00000",
                            19,
                            np.nan,
                            1,
                            0,
                            7.5,
                            1,
                        ]
                    ],
                    columns=custom_gtfs_package.stop_times.columns,
                ),
            ]
        )

        city_data_builder = CityDataBuilder(
            krakow_city_configuration,
            Weekday.MONDAY,
            is_today=False,
            custom_gtfs_package=custom_gtfs_package,
        )

        # Act
        with pytest.raises(
            TramStopNotFound, match="Stop stop_000_00000 not found in any mapping."
        ):
            city_data_builder.tram_routes_data

        # Assert
        get_relations_and_stops_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name,
            [1770194211, 2163355814, 10020926691, 2163355821, 2375524420, 629106153],
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name
        )
        gtfs_package_from_url_mock.assert_called_once_with(
            krakow_city_configuration.gtfs_url
        )
