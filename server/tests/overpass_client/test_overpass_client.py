from unittest.mock import MagicMock, patch

import overpy
from src.overpass_client import OverpassClient


class TestOverpassClient:
    AREA_NAME = "Some area"
    CUSTOM_NODE_IDS = [1, 2, 3, 4]

    EXPECTED_RELATIONS_AND_STOPS_QUERY = """
    [out:json];
    area["name"="Some area"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        node(id:1, 2, 3, 4)(area.search_area);
    );
    out geom;
    """

    @patch.object(overpy.Overpass, "query")
    def test_get_relations_and_stops(
        self, query_mock: MagicMock, overpass_query_result: overpy.Result
    ):
        # Arrange
        query_mock.return_value = overpass_query_result

        # Act
        query_result = OverpassClient.get_relations_and_stops(
            self.AREA_NAME, self.CUSTOM_NODE_IDS
        )

        # Assert
        assert query_result is overpass_query_result
        query_mock.assert_called_once_with(self.EXPECTED_RELATIONS_AND_STOPS_QUERY)
