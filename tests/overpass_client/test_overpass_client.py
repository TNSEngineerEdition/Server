from unittest.mock import MagicMock, patch

import overpy
import pytest

from city_configuration import TransitType
from overpass_client.overpass_client import OverpassClient


class TestOverpassClient:
    RELATIONS_AREA_NAME = "Some relations area"
    STOPS_AREA_NAME = "Some stops area"
    NETWORK = "Some network"

    @pytest.mark.parametrize(
        (
            "transit_type",
            "relations_area_name",
            "stops_area_name",
            "network",
            "custom_node_ids",
            "expected_query",
        ),
        [
            pytest.param(
                TransitType.TRAM,
                RELATIONS_AREA_NAME,
                STOPS_AREA_NAME,
                NETWORK,
                [1, 2, 3, 4],
                """
                [out:json][timeout:600];
                area["name"="Some relations area"]->.search_area;
                (
                    relation["route"="tram"](area.search_area);
                    node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
                    node(id:1, 2, 3, 4)(area.search_area);
                );
                out geom;
                """,
                id="custom_node_ids with content",
            ),
            pytest.param(
                TransitType.TRAM,
                RELATIONS_AREA_NAME,
                STOPS_AREA_NAME,
                NETWORK,
                [],
                """
                [out:json][timeout:600];
                area["name"="Some relations area"]->.search_area;
                (
                    relation["route"="tram"](area.search_area);
                    node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
                );
                out geom;
                """,
                id="empty custom_node_ids",
            ),
        ],
    )
    @patch.object(overpy.Overpass, "query")
    def test_get_relations_and_stops(
        self,
        query_mock: MagicMock,
        relations_and_stops_overpass_query_result: overpy.Result,
        transit_type: TransitType,
        relations_area_name: str,
        stops_area_name: str,
        network: str,
        custom_node_ids: list[int],
        expected_query: str,
    ) -> None:
        # Arrange
        query_mock.return_value = relations_and_stops_overpass_query_result

        # Act
        query_result = OverpassClient.get_relations_and_stops(
            transit_type,
            network,
            relations_area_name,
            stops_area_name,
            tuple(custom_node_ids),
        )

        # Assert
        assert query_result is relations_and_stops_overpass_query_result
        query_mock.assert_called_once_with(expected_query.replace(" " * 16, " " * 4))

    @patch.object(overpy.Overpass, "query")
    def test_get_tram_stops_and_tracks(
        self,
        query_mock: MagicMock,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
    ) -> None:
        # Arrange
        expected_query = """
        [out:json][timeout:600];
        area["name"="Some relations area"]->.search_area;
        (
            way["railway"="tram"](area.search_area);
            node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        );
        (._; >;);
        out geom;
        """

        query_mock.return_value = tram_stops_and_tracks_overpass_query_result

        # Act
        query_result = OverpassClient.get_tram_stops_and_tracks(
            self.RELATIONS_AREA_NAME
        )

        # Assert
        assert query_result is tram_stops_and_tracks_overpass_query_result
        query_mock.assert_called_once_with(expected_query.replace(" " * 8, " " * 4))
