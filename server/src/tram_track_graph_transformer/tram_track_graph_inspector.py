from functools import cached_property

import networkx as nx
from networkx.exception import NetworkXNoPath
from pyproj import Geod
from src.tram_track_graph_transformer.exceptions import (
    NodeNotFoundError,
    NoPathFoundError,
    PathTooLongError,
)
from src.tram_track_graph_transformer.node import Node


class TramTrackGraphInspector:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.geod = Geod(ellps="WGS84")

    @cached_property
    def _nodes_by_id(self) -> dict[int, Node]:
        return {node.id: node for node in self.graph.nodes}

    def shortest_path_between_nodes(
        self, start_node: Node, end_node: Node
    ) -> list[Node]:
        return nx.astar_path(
            self.graph,
            start_node,
            end_node,
            heuristic=lambda u, v: self.geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
            weight=lambda u, v, _: self.geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def check_path_viability(self, start_id: int, end_id: int, ratio: float):
        if (start_node := self._nodes_by_id.get(start_id)) is None:
            raise NodeNotFoundError(start_id)
        if (end_node := self._nodes_by_id.get(end_id)) is None:
            raise NodeNotFoundError(end_id)

        try:
            path = self.shortest_path_between_nodes(start_node, end_node)
        except NetworkXNoPath:
            raise NoPathFoundError(start_id, end_id)

        straight_line_distance = self.geod.inv(
            start_node.lon, start_node.lat, end_node.lon, end_node.lat
        )[2]

        path_length = self.geod.line_length(
            lons=[node.lon for node in path], lats=[node.lat for node in path],
        )
        if path_length > straight_line_distance * ratio:
            raise PathTooLongError(
                start_id, end_id, path_length, straight_line_distance * ratio
            )
