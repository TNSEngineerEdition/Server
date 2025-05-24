import math

import networkx as nx
import overpy
from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point

from src.city_data_builder import CityConfiguration
from src.tram_track_graph_transformer.exceptions import (
    TrackDirectionChangeError,
)
from src.tram_track_graph_transformer.node import Node
from src.tram_track_graph_transformer.node_type import NodeType


class TramTrackGraphTransformer:
    """
    TramTrackGraphTransformer processes OpenStreetMap (OSM) tram infrastructure data
    and transforms it into a directed NetworkX graph, where nodes are represented by Node
    instances. Under the hood it builds a directed graph using OSM tram track ways and
    includes the opposite direction where specified.

    In order to maintain the skeleton of the graph, nodes which are crucial to data
    consistency, such as intersections or tram stops, are marked as permanent and
    have to appear in the resulting graphs on their predefined positions. The IDs of
    permanent nodes are available via the `permanent_nodes` property.

    This class also allows for graph densification operations, for example by setting
    the max distance between two neighboring nodes with `densify_graph_by_max_distance`.
    These methods return new graph instances with modified graph topology depending
    on the called method.
    """

    _geod = Geod(ellps="WGS84")
    _transformer = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
    _inverse_transformer = Transformer.from_crs(
        "EPSG:2180", "EPSG:4326", always_xy=True
    )

    def __init__(
        self,
        tram_stops_and_tracks: overpy.Result,
        city_configuration: CityConfiguration,
    ):
        self._city_configuration = city_configuration
        self._ways = tram_stops_and_tracks.get_ways()
        self._nodes_by_id = {
            node.id: Node(
                id=node.id,
                lat=float(node.lat),
                lon=float(node.lon),
                type=self._get_node_type(node),
                name=node.tags.get("name"),
            )
            for node in tram_stops_and_tracks.get_nodes()
        }
        self._tram_track_graph = self._build_tram_track_graph_from_osm_ways()
        self._permanent_nodes = self._find_permanent_nodes()
        self._max_node_id = max(node.id for node in self._permanent_nodes)

    @staticmethod
    def _get_max_speed_for_way(
        way: overpy.Way, ratio: float = 3.6, default_speed: float = 50.0
    ) -> float:
        try:
            max_speed = float(way.tags.get("maxspeed"))
        except (ValueError, TypeError):
            max_speed = default_speed
        return max_speed / ratio

    def _build_tram_track_graph_from_osm_ways(self):
        graph = nx.DiGraph()

        for way in self._ways:
            node_ids = [self._nodes_by_id[node.id] for node in way.get_nodes()]
            is_oneway = way.tags.get("oneway") == "yes"
            max_speed = self._get_max_speed_for_way(way)

            for i in range(len(node_ids) - 1):
                source_node = node_ids[i]
                destination_node = node_ids[i + 1]

                graph.add_edge(source_node, destination_node, max_speed=max_speed)
                if not is_oneway:
                    graph.add_edge(destination_node, source_node, max_speed=max_speed)

        return graph

    def _get_node_type(self, node: Node):
        """
        OSM node IDs mentioned in `custom_stop_mapping` field of `CityConfiguration`
        should always have a type of `NodeType.TRAM_STOP`. This is due to these nodes
        being used for tram stop mapping between GTFS and OSM, which means that
        each node can potentially act as a tram stop, even when it has a different type
        assigned to it by OSM.
        """
        return (
            NodeType.TRAM_STOP
            if node.id in self._city_configuration.custom_stop_mapping.values()
            else NodeType.get_by_value_safe(node.tags.get("railway"))
        )

    def _get_tram_stop_node_ids_in_graph(self):
        """
        Returns set of tram stop nodes which are on the tram tracks provided by OSM.
        In case a track is out of service, the tram stops won't be used but
        will still be present in `self._stops`, so we want to exclude them.
        """

        return {
            node
            for node in self._nodes_by_id.values()
            if node.type == NodeType.TRAM_STOP and node in self._tram_track_graph.nodes
        }

    def _get_track_crossing_and_endpoint_node_ids(self):
        """
        Returns set of nodes which serving the function of track crossings or endpoints.
        A node is a crossing if it has more than 2 distinct neighbors.
        A node is a track endpoint when it has exactly 1 distinct neighbor.
        In case a node doesn't have any neighbors (which shouldn't happen),
        it's treated as an endpoint as well. Node A is a neighbor of node B
        when in a directed graph there exists an edge (A, B) or (B, A).
        """

        result: set[Node] = set()
        for node in self._tram_track_graph.nodes:
            predecessors = set(self._tram_track_graph.predecessors(node))
            successors = set(self._tram_track_graph.successors(node))
            if len(predecessors | successors) != 2:
                result.add(node)

        return result

    def _find_permanent_nodes(self):
        """
        Permanent nodes are used in `densify_graph_by_max_distance`.
        These nodes cannot be removed during the graph transformation process.
        Between them, the graph will be densified.
        """

        tram_stops = self._get_tram_stop_node_ids_in_graph()
        crossings = self._get_track_crossing_and_endpoint_node_ids()

        return tram_stops | crossings

    def _find_path_between_permanent_nodes(
        self, permanent_node: Node, successor: Node
    ) -> list[tuple[Node, float]]:
        """
        Finds the first different permanent node reachable from provided
        `permanent_node` via provided `successor` without backtracking.
        """

        path_coords_with_speed = [(permanent_node, 0.0)]
        previous_node, current_node = permanent_node, successor
        current_speed = self._tram_track_graph.get_edge_data(
            previous_node, current_node
        )["max_speed"]
        while current_node not in self._permanent_nodes:
            path_coords_with_speed.append((current_node, current_speed))
            next_candidate = next(
                filter(
                    lambda x: x != previous_node,
                    self._tram_track_graph.successors(current_node),
                ),
                None,
            )

            if next_candidate is None:
                raise TrackDirectionChangeError(permanent_node.id, current_node.id)
            current_speed = self._tram_track_graph.get_edge_data(
                current_node, next_candidate
            )["max_speed"]
            previous_node, current_node = current_node, next_candidate

        path_coords_with_speed.append((current_node, current_speed))
        return path_coords_with_speed

    @classmethod
    def _interpolate_path_nodes(
        cls, path_nodes: list[tuple[Node, float]], max_distance_in_meters: float
    ) -> list[tuple[tuple[float, float], float]]:
        meter_coords = [
            cls._transformer.transform(node.lon, node.lat) for node, _ in path_nodes
        ]
        line = LineString(meter_coords)

        if line.length <= max_distance_in_meters:
            return [
                (path_nodes[0][0].coordinates, path_nodes[0][1]),
                (path_nodes[-1][0].coordinates, path_nodes[-1][1]),
            ]

        segment_count = math.ceil(line.length / max_distance_in_meters)
        segment_size = line.length / segment_count

        interpolated_points = [
            line.interpolate(i * segment_size) for i in range(1, segment_count)
        ]

        interpolated_path_with_speed: list[tuple[tuple[float, float], float]] = [
            (path_nodes[0][0].coordinates, path_nodes[0][1])
        ]
        cumulative_distance = [0.0]
        for i in range(1, len(meter_coords)):
            prev = Point(meter_coords[i - 1])
            curr = Point(meter_coords[i])
            cumulative_distance.append(cumulative_distance[-1] + prev.distance(curr))

        segment_index = 0
        for p in interpolated_points:
            distance_to_p = line.project(p)
            while (
                segment_index < len(cumulative_distance) - 2
            ) and cumulative_distance[segment_index + 1] < distance_to_p:
                segment_index += 1

            speed = path_nodes[segment_index + 1][1]
            lat_lon = cls._inverse_transformer.transform(p.x, p.y)[::-1]
            interpolated_path_with_speed.append((lat_lon, speed))

        interpolated_path_with_speed.append(
            (path_nodes[-1][0].coordinates, path_nodes[-1][1])
        )
        return interpolated_path_with_speed

    def _get_new_node_id(self):
        self._max_node_id += 1
        return self._max_node_id

    @classmethod
    def _add_geodetic_edge(
        cls, graph: nx.DiGraph, source_node: Node, dest_node: Node, max_speed: float
    ):
        azimuth, _, length = cls._geod.inv(
            source_node.lon,
            source_node.lat,
            dest_node.lon,
            dest_node.lat,
        )
        graph.add_edge(
            source_node, dest_node, azimuth=azimuth, length=length, max_speed=max_speed
        )

    def _add_interpolated_nodes_path(
        self,
        densified_graph: nx.DiGraph,
        interpolated_node_coords_with_speed: list[tuple[tuple[float, float], float]],
        nodes_by_coordinates: dict[tuple[float, float], Node],
        first_node: Node,
        last_node: Node,
    ):
        previous_graph_node = first_node

        for (lat, lon), max_speed in interpolated_node_coords_with_speed[1:-1]:
            if (lat, lon) in nodes_by_coordinates:
                new_node = nodes_by_coordinates[(lat, lon)]
            else:
                new_node = Node(
                    id=self._get_new_node_id(),
                    lat=lat,
                    lon=lon,
                    type=NodeType.INTERPOLATED,
                )
                nodes_by_coordinates[(lat, lon)] = new_node

            self._add_geodetic_edge(
                densified_graph, previous_graph_node, new_node, max_speed
            )
            previous_graph_node = new_node

        (lat, lon), max_speed = interpolated_node_coords_with_speed[-1]
        if (lat, lon) in nodes_by_coordinates:
            last_node = nodes_by_coordinates[(lat, lon)]

        self._add_geodetic_edge(
            densified_graph, previous_graph_node, last_node, max_speed
        )

    def densify_graph_by_max_distance(
        self, max_distance_in_meters: float
    ) -> nx.DiGraph:
        """
        Builds a directed graph by splitting edges between permanent nodes
        into smaller segments based on `max_distance_in_meters`.
        Nodes: instances of the Node class
        Edges: no attributes.
        """

        if max_distance_in_meters <= 0:
            raise ValueError("max_distance_in_meters must be greater than 0.")

        densified_graph = nx.DiGraph()
        nodes_by_coordinates: dict[tuple[float, float], Node] = {}
        errors: list[TrackDirectionChangeError] = []

        for permanent_node in self._permanent_nodes:
            for successor in self._tram_track_graph.successors(permanent_node):
                try:
                    path_nodes = self._find_path_between_permanent_nodes(
                        permanent_node, successor
                    )
                except TrackDirectionChangeError as e:
                    errors.append(e)
                    continue

                interpolated_node_coords_with_speed = self._interpolate_path_nodes(
                    path_nodes, max_distance_in_meters
                )
                self._add_interpolated_nodes_path(
                    densified_graph,
                    interpolated_node_coords_with_speed,
                    nodes_by_coordinates,
                    permanent_node,
                    path_nodes[-1][0],
                )

        if errors:
            raise ExceptionGroup("Track direction errors during densification", errors)
        return densified_graph
