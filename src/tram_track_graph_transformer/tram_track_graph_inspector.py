from functools import cached_property

import networkx as nx
from networkx.exception import NetworkXNoPath
from pyproj import Geod

from tram_track_graph_transformer.exceptions import (
    NodeNotFoundError,
    NoPathFoundError,
    PathTooLongError,
)
from tram_track_graph_transformer.node import Node


class TramTrackGraphInspector:
    def __init__(self, graph: "nx.DiGraph[Node]"):
        self._graph = graph
        self._geod = Geod(ellps="WGS84")

    @cached_property
    def _nodes_by_id(self) -> dict[int, Node]:
        return {node.id: node for node in self._graph.nodes}

    @staticmethod
    def get_unique_tram_stop_pairs(
        stop_nodes_by_gtfs_trip_id: dict[str, list[int]],
    ) -> set[tuple[int, int]]:
        return {
            (stop_ids[i], stop_ids[i + 1])
            for stop_ids in stop_nodes_by_gtfs_trip_id.values()
            for i in range(len(stop_ids) - 1)
        }

    def shortest_path_between_nodes(
        self, start_node: Node, end_node: Node
    ) -> list[Node]:
        return nx.astar_path(
            self._graph,
            start_node,
            end_node,
            heuristic=lambda u, v: self._geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
            weight=lambda u, v, _: self._geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def check_path_viability(
        self, start_stop_id: int, end_stop_id: int, max_distance_ratio: float
    ) -> None:
        if (start_node := self._nodes_by_id.get(start_stop_id)) is None:
            raise NodeNotFoundError(start_stop_id)
        if (end_node := self._nodes_by_id.get(end_stop_id)) is None:
            raise NodeNotFoundError(end_stop_id)

        try:
            path = self.shortest_path_between_nodes(start_node, end_node)
        except NetworkXNoPath:
            raise NoPathFoundError(start_stop_id, end_stop_id)

        straight_line_distance = self._geod.inv(
            start_node.lon, start_node.lat, end_node.lon, end_node.lat
        )[2]

        path_distance = self._geod.line_length(
            lons=[node.lon for node in path],
            lats=[node.lat for node in path],
        )
        if path_distance > straight_line_distance * max_distance_ratio:
            raise PathTooLongError(
                start_stop_id,
                end_stop_id,
                path_distance,
                straight_line_distance * max_distance_ratio,
            )
