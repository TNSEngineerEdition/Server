from typing import Any

import pytest

from tram_track_graph_transformer.node import Node
from tram_track_graph_transformer.node_type import NodeType


class TestNode:
    EXAMPLE_NODE = Node(id=1234, lat=50.1234, lon=20.4321, type=NodeType.SWITCH)

    EQ_HASH_PARAMETRIZATION = [
        (EXAMPLE_NODE, True),
        (
            Node(id=1234, lat=50.1234, lon=20.4321, type=NodeType.TRAM_CROSSING),
            True,
        ),
        (Node(id=4321, lat=50.1234, lon=20.4321, type=NodeType.SWITCH), False),
        (1234, True),
        (4321, False),
        ("1234", False),
    ]

    def test_coordinates(self) -> None:
        # Act
        lat, lon = self.EXAMPLE_NODE.coordinates

        # Assert
        assert lat == 50.1234
        assert lon == 20.4321

    @pytest.mark.parametrize(("other", "is_equal"), EQ_HASH_PARAMETRIZATION)
    def test_eq(self, other: Any, is_equal: bool) -> None:
        # Assert
        assert self.EXAMPLE_NODE == other if is_equal else self.EXAMPLE_NODE != other

    @pytest.mark.parametrize(("other", "is_equal"), EQ_HASH_PARAMETRIZATION)
    def test_hash(self, other: Any, is_equal: bool) -> None:
        # Assert
        assert (
            hash(self.EXAMPLE_NODE) == hash(other)
            if is_equal
            else hash(self.EXAMPLE_NODE) != hash(other)
        )
