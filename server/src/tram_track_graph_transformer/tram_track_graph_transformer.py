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
            node.id: (float(node.lat), float(node.lon)) for node in self._coords_data
        }

        self._tram_track_graph = self._build_tram_track_graph_from_osm_ways()
        self._permanent_nodes = self._find_permanent_nodes()

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

    @property
    def permanent_node_ids(self):
        return self._permanent_nodes.copy()

    def _interpolate_between_first_and_last_node(self, latlon, max_distance_in_meters):
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

    def _densify_graph_by_max_distance(self, max_distance_in_meters):
        """
        Builds a new directed graph where each segment between permanent nodes is split
        into smaller segments according to the specified distance limit.

        Args:
            max_distance_in_meters (float):
                The maximum allowed distance between consecutive points after interpolation.

        Returns:
            networkx.DiGraph:
                The newly built, interpolated directed graph.
        """
        new_graph = nx.DiGraph()
        new_node_id_counter = max(self._permanent_nodes) + 1
        coord_map = {}

        for permanent_node in self._permanent_nodes:
            for successor in self._tram_track_graph.successors(permanent_node):
                path_coordinates = [self._node_coordinates_by_id[permanent_node]]

                current_node = successor
                previous_node = permanent_node
                path_found = True

                while current_node not in self._permanent_nodes:
                    path_coordinates.append(self._node_coordinates_by_id[current_node])
                    successors_list = list(
                        self._tram_track_graph.successors(current_node)
                    )

                    for next_candidate in successors_list:
                        if next_candidate != previous_node:
                            previous_node = current_node
                            current_node = next_candidate
                            break
                    else:
                        path_found = False
                        break

                if not path_found:
                    continue

                path_coordinates.append(self._node_coordinates_by_id[current_node])

                interpolated_nodes = self._interpolate_between_first_and_last_node(
                    path_coordinates, max_distance_in_meters
                )

                previous_graph_node = None
                for i, (lat, lon) in enumerate(interpolated_nodes):
                    is_first = i == 0
                    is_last = i == len(interpolated_nodes) - 1

                    if is_first:
                        new_graph.add_node(permanent_node, lat=lat, lon=lon)
                        previous_graph_node = permanent_node

                    elif is_last:
                        if (lat, lon) in coord_map:
                            last_graph_node = coord_map[(lat, lon)]
                        else:
                            last_graph_node = current_node
                            new_graph.add_node(last_graph_node, lat=lat, lon=lon)

                        new_graph.add_edge(previous_graph_node, last_graph_node)

                    else:
                        if (lat, lon) in coord_map:
                            new_node = coord_map[(lat, lon)]
                            new_graph.add_node(new_node, lat=lat, lon=lon)
                        else:
                            new_node = new_node_id_counter
                            coord_map[(lat, lon)] = new_node
                            new_graph.add_node(new_node, lat=lat, lon=lon)
                            new_node_id_counter += 1

                        new_graph.add_edge(previous_graph_node, new_node)
                        previous_graph_node = new_node
        return new_graph
