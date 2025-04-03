import math

import networkx as nx
import overpy
from pyproj import Transformer
from shapely.geometry import LineString

from .exceptions import TrackDirectionChangeError
from .model import Node


class TramTrackGraphTransformer:
    """
    TramTrackGraphTransformer processes OpenStreetMap (OSM) tram infrastructure data
    and transforms it into a directed NetworkX graph optimized for routing and analysis.

    It operates in two main stages:

        1. Skeleton graph construction:
        - Builds a directed graph (_tram_track_graph) from tram track OSM ways.
        - Retains only "permanent nodes", which include tram stops and track crossings
            or endpoints, to create a simplified base graph.

        2. Graph densification:
        - Splits long track segments between permanent nodes into shorter segments using geographic interpolation.
        - Ensures no edge exceeds a specified maximum distance, improving spatial resolution for analysis.

    This approach balances graph simplicity and geometric accuracy, making the resulting graph suitable for routing,
    visualization, and network algorithms.
    """

    def __init__(self, tram_stops_and_tracks: overpy.Result):
        self._ways = tram_stops_and_tracks.get_ways()
        self._nodes_by_id = {
            node.id: Node(
                id=node.id,
                lat=float(node.lat),
                lon=float(node.lon),
                type=node.tags.get("railway", ""),
            )
            for node in tram_stops_and_tracks.get_nodes()
        }
        self._tram_track_graph = self._build_tram_track_graph_from_osm_ways()
        self._permanent_nodes = self._find_permanent_nodes()

    def _build_tram_track_graph_from_osm_ways(self):
        graph = nx.DiGraph()

        for way in self._ways:
            node_ids = [self._nodes_by_id[node.id] for node in way.get_nodes()]
            is_oneway = way.tags.get("oneway") == "yes"

            for i in range(len(node_ids) - 1):
                source_node = node_ids[i]
                destination_node = node_ids[i + 1]

                graph.add_edge(source_node, destination_node)
                if not is_oneway:
                    graph.add_edge(destination_node, source_node)

        return graph

    def _get_tram_stop_node_ids_in_graph(self):
        """
        Returns set of tram stop node which are on the tram tracks provided by OSM.
        In case a track is out of service, the tram stops won't be used but
        will still be present in `self._stops`, so we want to exclude them.
        """

        return {
            node
            for node in self._nodes_by_id.values()
            if node.type == "tram_stop" and node in self._tram_track_graph.nodes
        }

    def _get_track_crossing_and_endpoint_node_ids(self):
        """
        Returns set of nodes which serveing the function of track crossings or endpoints.
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

    def _find_path_between_permenent_nodes(
        self, permanent_node: Node, successor: Node
    ) -> tuple[list[int], Node]:
        path_coordinates = [(permanent_node.lat, permanent_node.lon)]
        current_node = successor
        previous_node = permanent_node

        while current_node not in self._permanent_nodes:
            path_coordinates.append((current_node.lat, current_node.lon))

            for next_candidate in self._tram_track_graph.successors(current_node):
                if next_candidate != previous_node:
                    previous_node = current_node
                    current_node = next_candidate
                    break
            else:
                raise TrackDirectionChangeError(current_node.id)

        path_coordinates.append((current_node.lat, current_node.lon))

        return path_coordinates, current_node

    def _interpolate_between_first_and_last_node(
        self, node_coordinates: list[tuple[float, float]], max_distance_in_meters: float
    ) -> list[tuple[float, float]]:

        transformer = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
        inverse = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True)

        meter_coords = [
            transformer.transform(lon, lat) for lat, lon in node_coordinates
        ]
        line = LineString(meter_coords)
        length = line.length

        if length <= max_distance_in_meters:
            return [node_coordinates[0], node_coordinates[-1]]

        num_segments = max(1, math.ceil(length / max_distance_in_meters))
        distances = [i * (length / num_segments) for i in range(1, num_segments)]

        interpolated_points = [line.interpolate(d) for d in distances]
        interpolated_latlon = [
            inverse.transform(p.x, p.y)[::-1] for p in interpolated_points
        ]

        return [node_coordinates[0]] + interpolated_latlon + [node_coordinates[-1]]

    def _add_interpolated_nodes_with_edges(
        self,
        densified_graph: nx.DiGraph,
        interpolated_nodes: list[tuple[float, float]],
        coord_map: dict[tuple[float, float], Node],
        new_node_id_counter: int,
        first_node: Node,
        last_node: Node,
    ) -> int:

        previous_graph_node = None
        for i, (lat, lon) in enumerate(interpolated_nodes):
            is_first = i == 0
            is_last = i == len(interpolated_nodes) - 1

            if is_first:
                densified_graph.add_node(first_node)
                previous_graph_node = first_node

            elif is_last:
                if (lat, lon) in coord_map:
                    last_graph_node = coord_map[(lat, lon)]
                else:
                    last_graph_node = last_node
                    densified_graph.add_node(last_graph_node)

                densified_graph.add_edge(previous_graph_node, last_graph_node)

            else:
                if (lat, lon) in coord_map:
                    new_node = coord_map[(lat, lon)]
                    densified_graph.add_node(new_node)
                else:
                    new_node = Node(
                        id=new_node_id_counter, lat=lat, lon=lon, type="interpolated"
                    )
                    coord_map[(lat, lon)] = new_node
                    densified_graph.add_node(new_node)
                    new_node_id_counter += 1

                densified_graph.add_edge(previous_graph_node, new_node)
                previous_graph_node = new_node

        return new_node_id_counter

    def densify_graph_by_max_distance(
        self, max_distance_in_meters: float
    ) -> nx.DiGraph:
        """
        Builds a new directed graph by splitting edges between permanent nodes
        into smaller segments based on max_distance_in_meters.
        Nodes: instances of the Node class with the following attributes:
            - id (int): unique node identifier.
            - lat (float): geographic latitude.
            - lon (float): geographic longitude.
            - type (str): type of the node, e.g., "tram_stop", "switch", etc.

        Edges: no attributes.
        """
        if max_distance_in_meters <= 0:
            raise ValueError("max_distance_in_meters must be greater than 0.")

        densified_graph: nx.DiGraph = nx.DiGraph()
        new_node_id_counter: int = max(node.id for node in self._permanent_nodes) + 1
        coord_map: dict[tuple[float, float], Node] = {}
        errors: list[TrackDirectionChangeError] = []

        for permanent_node in self._permanent_nodes:
            for successor in self._tram_track_graph.successors(permanent_node):
                try:
                    path_coordinates, last_node = (
                        self._find_path_between_permenent_nodes(
                            permanent_node, successor
                        )
                    )

                    interpolated_nodes = self._interpolate_between_first_and_last_node(
                        path_coordinates, max_distance_in_meters
                    )
                    new_node_id_counter = self._add_interpolated_nodes_with_edges(
                        densified_graph,
                        interpolated_nodes,
                        coord_map,
                        new_node_id_counter,
                        permanent_node,
                        last_node,
                    )
                except TrackDirectionChangeError as e:
                    errors.append(e)
        if errors:
            raise ExceptionGroup("Track direction errors during densification", errors)

        return densified_graph
