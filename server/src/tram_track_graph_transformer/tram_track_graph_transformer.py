import math

import networkx as nx
import overpy
from pyproj import Transformer
from shapely.geometry import LineString


class TramTrackGraphTransformer:
    """
    TramTrackGraphTransformer converts OSM data into a directed NetworkX graph in two main stages:

        1. Skeleton graph construction:
        - Builds an initial graph (_tram_track_graph) using only main nodes — tram stops and tram track intersections.

        2. Graph densification:
        - Using the `densify_graph_by_max_distance` method, the graph is densified by adding  intermediate nodes so that the distance between consecutive nodes does not exceed the specified threshold.
    """

    def __init__(self, tram_stops_and_tracks: overpy.Result):
        self._ways = tram_stops_and_tracks.get_ways()
        self._stops = [
            node
            for node in tram_stops_and_tracks.get_nodes()
            if node.tags.get("railway") == "tram_stop"
        ]
        self._coords_data = tram_stops_and_tracks.get_nodes()
        self._node_coordinates_by_id = {
            node.id: (float(node.lat), float(node.lon))
            for node in self._coords_data
            if node.lat is not None and node.lon is not None
        }

        self._tram_track_graph = self._build_tram_track_graph_from_osm_ways()
        self._permanent_nodes = self._find_permanent_nodes()
        self._minified_tram_track_graph = self._build_minified_tram_track_graph()

    def _build_tram_track_graph_from_osm_ways(self):
        graph = nx.DiGraph()

        for way in self._ways:
            node_ids = [node.id for node in way.get_nodes()]
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
        Returns tram stop node IDs which are on the tram tracks provided by OSM.
        In case a track is out of service, the tram stops won't be used but
        will still be present in `self._stops`, so we want to exclude them.
        """

        return {
            stop.id for stop in self._stops if stop.id in self._tram_track_graph.nodes
        }

    def _get_track_crossing_and_endpoint_node_ids(self):
        """
        Returns node IDs which serve the function of track crossings or endpoints.
        A node is a crossing if it has more than 2 distinct neighbors.
        A node is a track endpoint when it has exactly 1 distinct neighbor.
        In case a node doesn't have any neighbors (which shouldn't happen),
        it's treated as an endpoint as well. Node A is a neighbor of node B
        when in a directed graph there exists an edge (A, B) or (B, A).
        """

        result: set[int] = set()
        for node in self._tram_track_graph:
            predecessors = set(self._tram_track_graph.predecessors(node))
            successors = set(self._tram_track_graph.successors(node))
            if len(predecessors | successors) != 2:
                result.add(node)

        return result

    def _find_permanent_nodes(self):
        """
        Permanent nodes form the basis for the `_minified_tram_track_graph`.
        These nodes cannot be removed during the graph transformation process.
        """

        tram_stops = self._get_tram_stop_node_ids_in_graph()
        crossings = self._get_track_crossing_and_endpoint_node_ids()

        return tram_stops | crossings

    def _reachable_permanent_nodes_dfs(self, source_node_id: int):
        result: set[int] = set()
        visited: set[int] = {source_node_id}

        stack: list[int] = list(self._tram_track_graph.successors(source_node_id))
        while stack:
            node = stack.pop()
            visited.add(node)

            if node in self._permanent_nodes:
                result.add(node)
                continue

            for item in filter(
                lambda x: x not in visited, self._tram_track_graph.successors(node)
            ):
                stack.append(item)

        return result

    def _build_minified_tram_track_graph(self):
        """
        Minified tram track graph contains only permanent nodes. If there exists
        an edge between two nodes in this graph, that means there is a path between
        two permanent nodes in the `_tram_track_graph`, which doesn't contain any
        other permanent nodes.
        """

        return nx.DiGraph(
            (source_node, destination_node)
            for source_node in self._permanent_nodes
            for destination_node in self._reachable_permanent_nodes_dfs(source_node)
        )

    def _add_coordinates_from_data(self):
        for node in self._minified_tram_track_graph.nodes:
            node_id = int(node)
            if node_id in self._node_coordinates_by_id:
                lat, lon = self._node_coordinates_by_id[node_id]
                self._minified_tram_track_graph.nodes[node]["lat"] = lat
                self._minified_tram_track_graph.nodes[node]["lon"] = lon

    def _tag_nodes_with_way_ids(self):
        for way in self._ways:
            way_id = way.id
            for node in way.nodes:
                node_id = node.id
                if node_id in self._minified_tram_track_graph.nodes:

                    if "ways" not in self._minified_tram_track_graph.nodes[node_id]:
                        self._minified_tram_track_graph.nodes[node_id]["ways"] = []
                    self._minified_tram_track_graph.nodes[node_id]["ways"].append(
                        way_id
                    )

    @property
    def permanent_node_ids(self):
        return self._permanent_nodes.copy()

    def densify_graph_by_max_distance(
        self, max_distance_in_meters: float
    ) -> nx.DiGraph:

        if max_distance_in_meters <= 0:
            raise ValueError("max_distance_in_meters must be a positive float value")

        def interpolate_between_first_and_last_node(
            path_with_coords, max_distance_in_meters
        ):
            latlon = [(lat, lon) for _, lat, lon in path_with_coords]

            transformer = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
            inverse = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True)

            meter_coords = [transformer.transform(lon, lat) for lat, lon in latlon]
            line = LineString(meter_coords)
            length = line.length

            if length <= max_distance_in_meters:
                return [latlon[0], latlon[-1]]

            num_segments = max(1, math.ceil(length / max_distance_in_meters))
            distances = [i * (length / num_segments) for i in range(1, num_segments)]

            interpolated_points = [line.interpolate(d) for d in distances]
            interpolated_latlon = [
                inverse.transform(p.x, p.y)[::-1] for p in interpolated_points
            ]

            return [latlon[0]] + interpolated_latlon + [latlon[-1]]

        new_graph = nx.DiGraph()
        new_id_counter = max(self._tram_track_graph.nodes) + 1

        for u in self._permanent_nodes:
            for v in self._tram_track_graph.successors(u):

                if self._tram_track_graph.has_edge(v, u):
                    continue

                path = [
                    (
                        u,
                        self._node_coordinates_by_id[u][0],
                        self._node_coordinates_by_id[u][1],
                    )
                ]
                node = v

                while node not in self._permanent_nodes:
                    path.append(
                        (
                            node,
                            self._node_coordinates_by_id[node][0],
                            self._node_coordinates_by_id[node][1],
                        )
                    )
                    node = list(self._tram_track_graph.successors(node))[0]

                path.append(
                    (
                        node,
                        self._node_coordinates_by_id[node][0],
                        self._node_coordinates_by_id[node][1],
                    )
                )
                interpolated_nodes = interpolate_between_first_and_last_node(
                    path, max_distance_in_meters
                )

                for i in range(len(interpolated_nodes)):
                    lat, lon = interpolated_nodes[i]
                    if i == 0:
                        new_graph.add_node(u, lat=lat, lon=lon, permanent=True)
                        prev_node = u
                    elif i == len(interpolated_nodes) - 1:
                        new_graph.add_node(node, lat=lat, lon=lon, permanent=True)
                        new_graph.add_edge(prev_node, node)
                    else:
                        new_graph.add_node(
                            new_id_counter, lat=lat, lon=lon, permanent=False
                        )
                        new_graph.add_edge(prev_node, new_id_counter)
                        prev_node = new_id_counter
                        new_id_counter += 1
        return new_graph
