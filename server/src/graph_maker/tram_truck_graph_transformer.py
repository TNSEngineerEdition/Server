import math

import networkx as nx
import overpy
import pyproj
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, transform


class TramTrackGraphTransformer:
    """
    TramTrackGraphTransformer converts OSM data into a directed NetworkX graph in two main stages:

        1. Skeleton graph construction:
        - Builds an initial graph (_graph) using only main nodes — tram stops and tram track intersections.

        2. Graph densification:
        - Using the `densify_graph_by_max_distance` method, the graph is densified by adding  intermediate nodes so that the distance between consecutive nodes does not exceed the specified threshold.
    """

    def __init__(self, tram_stops_and_tracks: overpy.Result):
        self._ways = tram_stops_and_tracks.ways
        self._stops = [
            node
            for node in tram_stops_and_tracks.nodes
            if node.tags.get("railway") == "tram_stop"
        ]
        self._coords_data = tram_stops_and_tracks.nodes
        self._graph = nx.DiGraph()
        self._pernament_nodes = []
        self._ways_dict = {}

        self._build_skeleton_graph()

    def _build_skeleton_graph(self):
        for way in self._ways:
            node_ids = [node.id for node in way.nodes]
            for i in range(len(node_ids) - 1):
                self._graph.add_edge(node_ids[i], node_ids[i + 1])

        self._pernament_nodes = self._find_pernament_nodes()
        self._remove_unnecessary_nodes()
        self._add_two_way_edges()
        self._add_coordinates_from_data()
        self._tag_nodes_with_way_ids()
        self._build_dict()
        while self._is_there_any_ways_to_merge():
            self._merge_ways(tolerance=2.0)

    @property
    def permanent_node_ids(self):
        return list(self._pernament_nodes)

    def densify_graph_by_max_distance(
        self, max_distance_in_meters: float
    ) -> nx.DiGraph:
        if max_distance_in_meters <= 0:
            raise ValueError("max_distance_in_meters must be a positive float value")

        graph_copy = self._graph.copy()
        self._subdivide_ways(graph_copy, max_distance=max_distance_in_meters)
        return graph_copy

    def _find_pernament_nodes(self):
        """
        Identifies main nodes in the _graph — nodes representing tram stops or railway crossings.
        These nodes form the basis for the initial _graph skeleton.
        They are essential for filtering out unnecessary nodes before the second stage of _graph creation,
        which involves densifying the network between main nodes.
        """
        result = [
            stop.id
            for stop in self._stops
            if stop.id in self._graph.nodes
            and (
                self._graph.out_degree(stop.id) > 0
                or self._graph.in_degree(stop.id) > 0
            )
        ]

        for node in self._graph.nodes:
            if self._graph.in_degree(node) > 1 or self._graph.out_degree(node) > 1:
                result.append(node)

        return result

    def _remove_unnecessary_nodes(self):
        start_nodes = [
            node for node in self._graph.nodes if self._graph.in_degree(node) == 0
        ]
        for node in start_nodes:
            to_remove = []
            successors = list(self._graph.successors(node))
            if node not in self._pernament_nodes:
                for successor in successors:
                    while (
                        successor not in self._pernament_nodes
                        and self._graph.out_degree(successor) > 0
                    ):
                        to_remove.append(successor)
                        successor = list(self._graph.successors(successor))
                        if len(successor) > 1:
                            break
                        successor = successor[0]
                    for i in to_remove:
                        self._graph.remove_node(i)
                    self._graph.add_edge(node, successor)

        for node in self._pernament_nodes:
            successors = list(self._graph.successors(node))
            for successor in successors:
                to_remove = []
                while (
                    successor not in self._pernament_nodes
                    and self._graph.out_degree(successor) > 0
                ):
                    to_remove.append(successor)
                    successor = list(self._graph.successors(successor))
                    if len(successor) > 1:
                        break
                    successor = successor[0]
                for i in to_remove:
                    self._graph.remove_node(i)
                self._graph.add_edge(node, successor)

    def _add_two_way_edges(self):
        for node in self._graph.nodes:
            for successor in self._graph.successors(node):
                for way in self._ways:
                    way_node_ids = [n.id for n in way.nodes]
                    if node in way_node_ids and successor in way_node_ids:
                        if way.tags.get("oneway") != "yes":
                            self._graph.add_edge(successor, node)
                        break

    def _is_there_any_ways_to_merge(self):
        for way_id in self._ways_dict:
            count = sum(
                1
                for _, data in self._graph.nodes(data=True)
                if way_id in data.get("ways", [])
            )
            if count < 2:
                return True
        return False

    def _add_coordinates_from_data(self):
        nodes_dict = {
            int(node.id): (float(node.lat), float(node.lon))
            for node in self._coords_data
            if node.lat is not None and node.lon is not None
        }

        for node in self._graph.nodes:
            node_id = int(node)
            if node_id in nodes_dict:
                lat, lon = nodes_dict[node_id]
                self._graph.nodes[node]["lat"] = lat
                self._graph.nodes[node]["lon"] = lon

    def _tag_nodes_with_way_ids(self):
        for way in self._ways:
            way_id = way.id
            for node in way.nodes:
                node_id = node.id
                if node_id in self._graph.nodes:

                    if "ways" not in self._graph.nodes[node_id]:
                        self._graph.nodes[node_id]["ways"] = []
                    self._graph.nodes[node_id]["ways"].append(way_id)

    def _build_dict(self):
        self._ways_dict = {}
        # słownik node_id -> (lon, lat)
        nodes_dict = {
            node.id: (float(node.lon), float(node.lat)) for node in self._coords_data
        }

        for way in self._ways:
            coords = []
            for node_id in way._node_ids:
                if node_id in nodes_dict:
                    coords.append(nodes_dict[node_id])
            if len(coords) < 2:
                continue

            linestring = LineString(coords)

            if way.id in self._ways_dict:
                existing = self._ways_dict[way.id]
                self._ways_dict[way.id] = linemerge([existing, linestring])
            else:
                self._ways_dict[way.id] = linestring

    def _merge_ways(self, tolerance=2.0):
        transformer = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        ).transform
        processed = set()
        next_way_id = max(self._ways_dict) + 1
        for way_id, geom in list(self._ways_dict.items()):
            if way_id in processed:
                continue

            start_pt = Point(geom.coords[0])
            end_pt = Point(geom.coords[-1])

            has_start = False
            has_end = False

            for node_id, data in self._graph.nodes(data=True):
                if way_id not in data.get("ways", []):
                    continue

                node_pt = Point(data["lon"], data["lat"])
                if node_pt.distance(start_pt) < 1e-6:
                    has_start = True
                if node_pt.distance(end_pt) < 1e-6:
                    has_end = True

            if has_start == has_end:
                continue

            free_end = end_pt if has_start else start_pt
            free_end_3857 = transform(transformer, free_end)

            for other_id, other_geom in self._ways_dict.items():
                if other_id == way_id or other_id in processed:
                    continue

                other_start = Point(other_geom.coords[0])
                other_end = Point(other_geom.coords[-1])
                other_start_3857 = transform(transformer, other_start)
                other_end_3857 = transform(transformer, other_end)

                dist_start = free_end_3857.distance(other_start_3857)
                dist_end = free_end_3857.distance(other_end_3857)

                if dist_start < tolerance or dist_end < tolerance:
                    g1 = geom.reverse() if not has_start else geom
                    g2 = other_geom

                    if dist_end < tolerance:
                        g2 = g2.reverse()

                    merged_geom = linemerge([g1, g2])
                    if isinstance(merged_geom, MultiLineString):
                        merged_geom = list(merged_geom.geoms)[0]
                    new_way_id = next_way_id
                    next_way_id += 1
                    self._ways_dict[new_way_id] = merged_geom
                    del self._ways_dict[way_id]
                    del self._ways_dict[other_id]

                    self._update_nodes_after_merge(way_id, other_id, new_way_id)

                    processed.update({way_id, other_id})
                    break

    def _update_nodes_after_merge(self, old_way_id_1, old_way_id_2, new_way_id):
        for node_id, data in self._graph.nodes(data=True):
            ways = data.get("ways", [])

            changed = False
            if old_way_id_1 in ways:
                ways.remove(old_way_id_1)
                changed = True
            if old_way_id_2 in ways:
                ways.remove(old_way_id_2)
                changed = True

            if changed:
                if new_way_id not in ways:
                    ways.append(new_way_id)
                data["ways"] = ways

    def _subdivide_ways(self, _graph: nx.DiGraph, max_distance: float):
        edges_to_remove = set()

        def find_existing_node_by_coords(lat, lon, tolerance=1e-6):
            for node_id, data in _graph.nodes(data=True):
                if (
                    abs(data.get("lat", 0) - lat) < tolerance
                    and abs(data.get("lon", 0) - lon) < tolerance
                ):
                    return node_id
            return None

        transformer_to_3857 = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        ).transform
        transformer_to_wgs = pyproj.Transformer.from_crs(
            "EPSG:3857", "EPSG:4326", always_xy=True
        ).transform

        next_node_id = max(_graph.nodes) + 1 if _graph.nodes else 1

        for way_id, geometry in self._ways_dict.items():
            if not isinstance(geometry, LineString):
                continue

            line_3857 = transform(transformer_to_3857, geometry)
            existing_points = []

            for node_id, data in _graph.nodes(data=True):
                if way_id in data.get("ways", []):
                    pt = transform(transformer_to_3857, Point(data["lon"], data["lat"]))
                    dist = line_3857.project(pt)
                    existing_points.append((node_id, dist))

            if len(existing_points) < 2:
                continue

            existing_points.sort(key=lambda x: x[1])

            for i in range(len(existing_points) - 1):
                node_a, dist_a = existing_points[i]
                node_b, dist_b = existing_points[i + 1]

                if dist_a > dist_b:
                    node_a, dist_a, node_b, dist_b = node_b, dist_b, node_a, dist_a

                segment_len = dist_b - dist_a
                n = math.ceil(segment_len / max_distance)

                if n == 1:
                    continue

                step = segment_len / n
                prev_node = node_a
                interpolated_nodes = []

                for k in range(1, n):
                    dist_current = dist_a + k * step
                    if dist_current >= dist_b:
                        _graph.add_edge(prev_node, node_b)
                        break

                    ip_3857 = line_3857.interpolate(dist_current)
                    ip_wgs = transform(transformer_to_wgs, ip_3857)
                    lat_new, lon_new = ip_wgs.y, ip_wgs.x

                    existing = find_existing_node_by_coords(lat_new, lon_new)
                    if existing:
                        new_node_id = existing
                    else:
                        new_node_id = next_node_id
                        next_node_id += 1
                        _graph.add_node(
                            new_node_id, lat=lat_new, lon=lon_new, ways=[way_id]
                        )
                    interpolated_nodes.append(new_node_id)

                all_nodes = [node_a] + interpolated_nodes + [node_b]

                if _graph.has_edge(node_a, node_b):
                    edges_to_remove.add((node_a, node_b))
                    for u, v in zip(all_nodes, all_nodes[1:]):
                        _graph.add_edge(u, v, ways=[way_id])

                if _graph.has_edge(node_b, node_a):
                    edges_to_remove.add((node_b, node_a))
                    for u, v in zip(reversed(all_nodes), list(reversed(all_nodes))[1:]):
                        _graph.add_edge(u, v, ways=[way_id])

        _graph.remove_edges_from(edges_to_remove)
