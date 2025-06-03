from unittest.mock import MagicMock, patch

import overpy
import pytest

from src.city_data_builder import CityConfiguration, CityDataBuilder
from src.tram_stop_mapper.gtfs_package import GTFSPackage
from src.tram_stop_mapper.weekday import Weekday


class TestCityDataBuilder:
    @pytest.mark.parametrize(
        ("weekday_enum", "expected_trip_count", "expected_stop_count"),
        [
            (Weekday.MONDAY, 4440, 115299),
            (Weekday.TUESDAY, 4440, 115299),
            (Weekday.WEDNESDAY, 4440, 115299),
            (Weekday.THURSDAY, 4440, 115299),
            (Weekday.FRIDAY, 4532, 117637),
            (Weekday.SATURDAY, 2666, 70424),
            (Weekday.SUNDAY, 2400, 63013),
        ],
    )
    @patch("src.tram_stop_mapper.gtfs_package.GTFSPackage.from_url")
    @patch("src.overpass_client.OverpassClient.get_tram_stops_and_tracks")
    @patch("src.overpass_client.OverpassClient.get_relations_and_stops")
    def test_city_data_builder(
        self,
        get_relations_and_stops_mock: MagicMock,
        get_tram_stops_and_tracks_mock: MagicMock,
        gtfs_package_from_url_mock: MagicMock,
        krakow_city_configuration: CityConfiguration,
        relations_and_stops_overpass_query_result: overpy.Result,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
        gtfs_package: GTFSPackage,
        weekday_enum: Weekday,
        expected_trip_count: int,
        expected_stop_count: int,
    ):
        # Arrange
        get_relations_and_stops_mock.return_value = (
            relations_and_stops_overpass_query_result
        )
        get_tram_stops_and_tracks_mock.return_value = (
            tram_stops_and_tracks_overpass_query_result
        )
        gtfs_package_from_url_mock.return_value = gtfs_package

        expected_node_count, expected_edge_count = 43227, 45953

        # Act
        city_data_builder = CityDataBuilder(
            krakow_city_configuration, weekday=weekday_enum
        )

        # Assert
        assert len(city_data_builder.tram_track_graph_data) == expected_node_count
        assert (
            sum(len(node.neighbors) for node in city_data_builder.tram_track_graph_data)
            == expected_edge_count
        )

        assert len(city_data_builder.tram_trips_data) == expected_trip_count
        assert (
            sum(len(trip.stops) for trip in city_data_builder.tram_trips_data)
            == expected_stop_count
        )

        assert all(trip.stops for trip in city_data_builder.tram_trips_data)

        get_relations_and_stops_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name,
            list(krakow_city_configuration.custom_stop_mapping.values()),
        )
        get_tram_stops_and_tracks_mock.assert_called_once_with(
            krakow_city_configuration.osm_area_name
        )
        gtfs_package_from_url_mock.assert_called_once_with(
            krakow_city_configuration.gtfs_url
        )
