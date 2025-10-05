from unittest.mock import MagicMock, patch

import overpy
import pytest

from city_data_builder import CityConfiguration, CityDataBuilder
from tram_stop_mapper import GTFSPackage, Weekday


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

    @pytest.mark.parametrize(
        (
            "weekday",
            "expected_route_count",
            "expected_trip_count",
            "expected_stop_count",
        ),
        [
            pytest.param(Weekday.MONDAY, 23, 4440, 115299, id=Weekday.MONDAY),
            pytest.param(Weekday.TUESDAY, 23, 4440, 115299, id=Weekday.TUESDAY),
            pytest.param(Weekday.WEDNESDAY, 23, 4440, 115299, id=Weekday.WEDNESDAY),
            pytest.param(Weekday.THURSDAY, 23, 4440, 115299, id=Weekday.THURSDAY),
            pytest.param(Weekday.FRIDAY, 26, 4532, 117637, id=Weekday.FRIDAY),
            pytest.param(Weekday.SATURDAY, 23, 2666, 70424, id=Weekday.SATURDAY),
            pytest.param(Weekday.SUNDAY, 23, 2400, 63013, id=Weekday.SUNDAY),
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
        city_data_builder = CityDataBuilder(krakow_city_configuration, weekday)

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

    @pytest.mark.parametrize(
        (
            "weekday",
            "expected_route_count",
            "expected_trip_count",
            "expected_stop_count",
        ),
        [
            pytest.param(Weekday.MONDAY, 22, 4144, 105853, id=Weekday.MONDAY),
            pytest.param(Weekday.TUESDAY, 22, 4144, 105853, id=Weekday.TUESDAY),
            pytest.param(Weekday.WEDNESDAY, 22, 4144, 105853, id=Weekday.WEDNESDAY),
            pytest.param(Weekday.THURSDAY, 22, 4144, 105853, id=Weekday.THURSDAY),
            pytest.param(Weekday.FRIDAY, 25, 4232, 108146, id=Weekday.FRIDAY),
            pytest.param(Weekday.SATURDAY, 22, 2453, 63712, id=Weekday.SATURDAY),
            pytest.param(Weekday.SUNDAY, 22, 2223, 57561, id=Weekday.SUNDAY),
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
            krakow_city_configuration, weekday, custom_gtfs_package=custom_gtfs_package
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
