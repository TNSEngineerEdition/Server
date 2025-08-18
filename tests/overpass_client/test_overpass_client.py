from unittest.mock import MagicMock, patch

import overpy
import pytest

from src.overpass_client import OverpassClient


class TestOverpassClient:
    AREA_NAME = "Some area"
    CUSTOM_NODE_IDS = [1, 2, 3, 4]

    EXPECTED_RELATIONS_AND_STOPS_QUERY = """
    [out:json][timeout:600];
    area["name"="Some area"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        node(id:1, 2, 3, 4)(area.search_area);
    );
    out geom;
    """

    @pytest.mark.parametrize(
        ("area_name", "custom_node_ids", "expected_query"),
        [
            pytest.param(
                "Some area",
                [1, 2, 3, 4],
                """
                [out:json][timeout:600];
                area["name"="Some area"]->.search_area;
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
                "Some area",
                [],
                """
                [out:json][timeout:600];
                area["name"="Some area"]->.search_area;
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
        area_name: str,
        custom_node_ids: list[int],
        expected_query: str,
    ):
        # Arrange
        query_mock.return_value = relations_and_stops_overpass_query_result

        # Act
        query_result = OverpassClient.get_relations_and_stops(
            area_name, custom_node_ids
        )

        # Assert
        assert query_result is relations_and_stops_overpass_query_result
        query_mock.assert_called_once_with(expected_query.replace(" " * 16, " " * 4))
