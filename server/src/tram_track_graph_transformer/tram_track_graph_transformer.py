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
            int(node.id): (float(node.lat), float(node.lon))
            for node in self._coords_data
            if node.lat is not None and node.lon is not None
        }
        self._ways_dict = self._build_ways_dict()

        self._tram_track_graph = self._build_tram_track_graph_from_osm_ways()
        self._permanent_nodes = self._find_permanent_nodes()
        self._minified_tram_track_graph = self._build_minified_tram_track_graph()
        self._add_coordinates_from_data()
        self._tag_nodes_with_way_ids()
        while self._is_there_any_ways_to_merge():
            self._merge_ways(tolerance=2.0)

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

    def _build_ways_dict(self):
        """
        Builds a dictionary mapping way IDs to LineString geometries using node coordinates.
        """
        ways_dict = {}
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

            if way.id in ways_dict:
                existing = ways_dict[way.id]
                ways_dict[way.id] = linemerge([existing, linestring])
            else:
                ways_dict[way.id] = linestring
        return ways_dict

    def _is_there_any_ways_to_merge(self):
        for way_id in self._ways_dict:
            count = sum(
                1
                for _, data in self._minified_tram_track_graph.nodes(data=True)
                if way_id in data.get("ways", [])
            )
            if count < 2:
                return True
        return False

    def _update_nodes_after_merge(self, old_way_id_1, old_way_id_2, new_way_id):
        for node_id, data in self._minified_tram_track_graph.nodes(data=True):
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

            for node_id, data in self._minified_tram_track_graph.nodes(data=True):
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

    @property
    def permanent_node_ids(self):
        return self._permanent_nodes.copy()

    def _subdivide_ways(self, _tram_track_graph: nx.DiGraph, max_distance: float):
        edges_to_remove = set()

        def find_existing_node_by_coords(lat, lon, tolerance=1e-6):
            for node_id, data in _tram_track_graph.nodes(data=True):
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

        next_node_id = (
            max(_tram_track_graph.nodes) + 1 if _tram_track_graph.nodes else 1
        )

        for way_id, geometry in self._ways_dict.items():
            if not isinstance(geometry, LineString):
                continue

            line_3857 = transform(transformer_to_3857, geometry)
            existing_points = []

            for node_id, data in _tram_track_graph.nodes(data=True):
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
                        _tram_track_graph.add_edge(prev_node, node_b)
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
                        _tram_track_graph.add_node(
                            new_node_id, lat=lat_new, lon=lon_new, ways=[way_id]
                        )
                    interpolated_nodes.append(new_node_id)

                all_nodes = [node_a] + interpolated_nodes + [node_b]

                if _tram_track_graph.has_edge(node_a, node_b):
                    edges_to_remove.add((node_a, node_b))
                    for u, v in zip(all_nodes, all_nodes[1:]):
                        _tram_track_graph.add_edge(u, v, ways=[way_id])

                if _tram_track_graph.has_edge(node_b, node_a):
                    edges_to_remove.add((node_b, node_a))
                    for u, v in zip(reversed(all_nodes), list(reversed(all_nodes))[1:]):
                        _tram_track_graph.add_edge(u, v, ways=[way_id])

        _tram_track_graph.remove_edges_from(edges_to_remove)

    def densify_graph_by_max_distance(
        self, max_distance_in_meters: float
    ) -> nx.DiGraph:
        if max_distance_in_meters <= 0:
            raise ValueError("max_distance_in_meters must be a positive float value")

        graph_copy = self._minified_tram_track_graph.copy()
        self._subdivide_ways(graph_copy, max_distance=max_distance_in_meters)
        return graph_copy
