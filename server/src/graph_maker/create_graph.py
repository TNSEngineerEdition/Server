import math

import folium
import networkx as nx
import pyproj
from model import NodeCoordinate, TrackGeometry, TramStop, Way
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, transform


class NetworkGraph:
    """
    NetworkGraph class creta a directed graph from OpenStreetMap data.
    To run this class and create a graph you need to provide two files:
    - ways_file: json file with ways data
    - stops_file: json file with stops data
    Those files you can download from notebook download_data.ipynb
    Then you can create a graph by calling create_graph method.

    *find_main_nodes method returns a list of main nodes in the graph -> crossroads and stops.
    *create_graph method creates a graph from ways and stops data:
    *remove_unnecessary_nodes method removes nodes that are not crossroads or stops from the graph:
        -first for loop iterarate through nodes that are not main nodes, but they are first at path
            so we can't remove them and connect them with main nodes
        -second for loop iterarate through main nodes and connect them with next main node
    *add_two_way_edges method adds two way edges to the graph if way is not one way :
        -we are looking for way where node and successor are in the same way
        -then we check if way is not one way and add edge from successor to node
    *add_coordinates_from_file method adds coordinates to the graph nodes from file
    *tag_nodes_with_way_ids method adds way ids to the nodes:
        -we are iterating through ways and nodes in way
        -then we are adding way id to the node
    *build_dict method creates a dictionary with ways ids as keys and geometry as values
    *is_there_any_ways_to_merge method checks if there are any ways to merge
    *merge_ways method merges ways that are close to each other:
        -we are iterating through ways and checking if there are ways that are close to each other
        -if there are we are merging them and updating nodes
    *update_nodes_after_merge method updates nodes after merge
    *subdivide_ways method divides ways into smaller parts:
        -we are iterating through ways and checking if there are nodes in the way
        -if there are we are dividing way into smaller parts
    *visualize_graph method visualizes the graph on the map
    """

    def __init__(
        self,
        ways_data: list[Way],
        stops_data: list[TramStop],
        coords_data: list[NodeCoordinate],
        geometry_data: TrackGeometry,
        max_distance=25.0,
    ):
        self.graph = nx.DiGraph()
        self.ways = ways_data
        self.stops = stops_data
        self.coords_data = coords_data
        self.geometry_data = geometry_data
        self.max_distance = max_distance
        self.main_nodes = []

    def find_main_nodes(self):
        result = [
            stop.id
            for stop in self.stops
            if stop.id in self.graph.nodes
            and (
                self.graph.out_degree(stop.id) > 0 or self.graph.in_degree(stop.id) > 0
            )
        ]

        for node in self.graph.nodes:
            if self.graph.in_degree(node) > 1 or self.graph.out_degree(node) > 1:
                result.append(node)

        return result

    def create_graph(self):
        for way in self.ways:
            nodes = way.nodes
            for i in range(len(nodes) - 1):
                self.graph.add_edge(nodes[i], nodes[i + 1])

        self.main_nodes = self.find_main_nodes()
        self.remove_unnecessary_nodes()
        self.add_two_way_edges()
        self.add_coordinates_from_data()
        self.tag_nodes_with_way_ids()
        self.build_dict()
        while self.is_there_any_ways_to_merge():
            self.merge_ways(tolerance=2.0)
        self.subdivide_ways(max_distance=self.max_distance)

    def remove_unnecessary_nodes(self):
        start_nodes = [
            node for node in self.graph.nodes if self.graph.in_degree(node) == 0
        ]
        for node in start_nodes:
            to_remove = []
            successors = list(self.graph.successors(node))
            if node not in self.main_nodes:
                for successor in successors:
                    while (
                        successor not in self.main_nodes
                        and self.graph.out_degree(successor) > 0
                    ):
                        to_remove.append(successor)
                        successor = list(self.graph.successors(successor))
                        if len(successor) > 1:
                            break
                        successor = successor[0]
                    for i in to_remove:
                        self.graph.remove_node(i)
                    self.graph.add_edge(node, successor)

        for node in self.main_nodes:
            successors = list(self.graph.successors(node))
            for successor in successors:
                to_remove = []
                while (
                    successor not in self.main_nodes
                    and self.graph.out_degree(successor) > 0
                ):
                    to_remove.append(successor)
                    successor = list(self.graph.successors(successor))
                    if len(successor) > 1:
                        break
                    successor = successor[0]
                for i in to_remove:
                    self.graph.remove_node(i)
                self.graph.add_edge(node, successor)

    def add_two_way_edges(self):
        for node in self.graph.nodes:
            for successor in self.graph.successors(node):
                for way in self.ways:
                    if node in way.nodes and successor in way.nodes:
                        if way.tags.get("oneway") != "yes":
                            self.graph.add_edge(successor, node)
                        break

    def is_there_any_ways_to_merge(self):
        for way_id in self.ways_dict:
            count = sum(
                1
                for _, data in self.graph.nodes(data=True)
                if way_id in data.get("ways", [])
            )
            if count < 2:
                return True
        return False

    def add_coordinates_from_data(self):
        nodes_dict = {node.id: (node.lat, node.lon) for node in self.coords_data}
        for node in self.graph.nodes:
            if node in nodes_dict:
                lat, lon = nodes_dict[node]
                self.graph.nodes[node]["lat"] = lat
                self.graph.nodes[node]["lon"] = lon

    def tag_nodes_with_way_ids(self):
        for way in self.ways:
            way_id = way.id
            for node_id in way.nodes:
                if node_id in self.graph.nodes:
                    if "ways" not in self.graph.nodes[node_id]:
                        self.graph.nodes[node_id]["ways"] = []
                    self.graph.nodes[node_id]["ways"].append(way_id)

    def build_dict(self):
        self.ways_dict = {}
        for feature in self.geometry_data.features:
            properties = feature.properties
            geometry = feature.geometry
            way_id = int(properties["id"])
            if geometry["type"] == "LineString":
                linestring = LineString(geometry["coordinates"])
            else:
                continue
            if way_id in self.ways_dict:
                existing = self.ways_dict[way_id]
                self.ways_dict[way_id] = linemerge([existing, linestring])
            else:
                self.ways_dict[way_id] = linestring

    def merge_ways(self, tolerance=2.0):
        transformer = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        ).transform
        processed = set()
        next_way_id = max(self.ways_dict) + 1
        for way_id, geom in list(self.ways_dict.items()):
            if way_id in processed:
                continue

            start_pt = Point(geom.coords[0])
            end_pt = Point(geom.coords[-1])

            has_start = False
            has_end = False

            for node_id, data in self.graph.nodes(data=True):
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

            for other_id, other_geom in self.ways_dict.items():
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
                    self.ways_dict[new_way_id] = merged_geom
                    del self.ways_dict[way_id]
                    del self.ways_dict[other_id]

                    self.update_nodes_after_merge(way_id, other_id, new_way_id)

                    processed.update({way_id, other_id})
                    break

    def update_nodes_after_merge(self, old_way_id_1, old_way_id_2, new_way_id):
        for node_id, data in self.graph.nodes(data=True):
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

    def subdivide_ways(self, max_distance=25.0):
        edges_to_remove = set()

        def find_existing_node_by_coords(lat, lon, tolerance=1e-6):
            for node_id, data in self.graph.nodes(data=True):
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
        next_node_id = max(self.graph.nodes) + 1
        for way_id, geometry in self.ways_dict.items():
            if not isinstance(geometry, LineString):
                continue

            line_3857 = transform(transformer_to_3857, geometry)

            existing_points = []
            for node_id, data in self.graph.nodes(data=True):
                if way_id in data.get("ways", []):
                    pt = transform(transformer_to_3857, Point(data["lon"], data["lat"]))
                    dist = line_3857.project(pt)
                    existing_points.append((node_id, dist))

            if len(existing_points) < 2:
                continue

            existing_points.sort(key=lambda x: x[1])
            for i in range(len(existing_points) - 1):
                node_1, dist_1 = existing_points[i]
                node_2, dist_2 = existing_points[i + 1]

                if dist_1 < dist_2:
                    node_a, dist_a = node_1, dist_1
                    node_b, dist_b = node_2, dist_2
                else:
                    node_a, dist_a = node_2, dist_2
                    node_b, dist_b = node_1, dist_1

                def ensure_node(node_id, dist):
                    if self.graph.has_node(node_id):
                        return node_id
                    pt = line_3857.interpolate(dist)
                    pt_wgs = transform(transformer_to_wgs, pt)
                    lat, lon = pt_wgs.y, pt_wgs.x
                    existing = find_existing_node_by_coords(lat, lon)
                    if existing:
                        return existing
                    self.graph.add_node(node_id, lat=lat, lon=lon, ways=[way_id])
                    return node_id

                node_a = ensure_node(node_a, dist_a)
                node_b = ensure_node(node_b, dist_b)

                was_ab = self.graph.has_edge(node_a, node_b)
                was_ba = self.graph.has_edge(node_b, node_a)

                segment_len = dist_b - dist_a
                n = math.ceil(segment_len / max_distance)
                if n == 1:
                    continue
                else:
                    step = segment_len / n
                    prev_node = node_a
                    interpolated_nodes = []
                    for k in range(1, n):
                        dist_current = dist_a + k * step
                        if dist_current >= dist_b:
                            self.graph.add_edge(prev_node, node_b)
                            break

                        ip_3857 = line_3857.interpolate(dist_current)
                        ip_wgs = transform(transformer_to_wgs, ip_3857)
                        lat_new, lon_new = ip_wgs.y, ip_wgs.x

                        new_node_id = next_node_id
                        next_node_id += 1
                        existing = find_existing_node_by_coords(lat_new, lon_new)
                        if existing:
                            new_node_id = existing
                        else:
                            self.graph.add_node(
                                new_node_id, lat=lat_new, lon=lon_new, ways=[way_id]
                            )
                        interpolated_nodes.append(new_node_id)
                    interpolated_nodes_ab = interpolated_nodes
                    interpolated_nodes_ba = interpolated_nodes[::-1]

                    if was_ab:
                        edges_to_remove.add((node_a, node_b))
                        prev = node_a
                        for node in interpolated_nodes_ab:
                            self.graph.add_edge(prev, node, ways=[way_id])
                            prev = node
                        self.graph.add_edge(prev, node_b, ways=[way_id])

                    if was_ba:
                        edges_to_remove.add((node_b, node_a))
                        prev = node_b
                        for node in interpolated_nodes_ba:
                            self.graph.add_edge(prev, node, ways=[way_id])
                            prev = node
                        self.graph.add_edge(prev, node_a, ways=[way_id])
        self.graph.remove_edges_from(edges_to_remove)

    def visualize_graph(self, map_filename="graph_map.html"):
        node_positions = {
            node: (data["lat"], data["lon"])
            for node, data in self.graph.nodes(data=True)
            if "lat" in data and "lon" in data
        }

        if not node_positions:
            raise ValueError("No node positions found")

        avg_lat = sum(pos[0] for pos in node_positions.values()) / len(node_positions)
        avg_lon = sum(pos[1] for pos in node_positions.values()) / len(node_positions)

        fmap = folium.Map(
            location=[avg_lat, avg_lon], zoom_start=14, min_zoom=2, control_scale=True
        )

        for u, v in self.graph.edges:
            if u in node_positions and v in node_positions:
                latlngs = [
                    (node_positions[u][0], node_positions[u][1]),
                    (node_positions[v][0], node_positions[v][1]),
                ]
                folium.PolyLine(
                    locations=latlngs, color="blue", weight=2, opacity=0.7
                ).add_to(fmap)
        for node in self.main_nodes:
            if node in node_positions:
                lat, lon = node_positions[node]
                folium.CircleMarker(
                    location=(lat, lon),
                    radius=4,
                    color="red",
                    fill=True,
                    fill_opacity=0.9,
                    popup=f"Main node: {node}",
                ).add_to(fmap)

        for node in self.graph.nodes:
            if node in node_positions and node not in self.main_nodes:
                lat, lon = node_positions[node]
                folium.CircleMarker(
                    location=(lat, lon),
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"New node: {node}",
                ).add_to(fmap)
        fmap.save(map_filename)
        print(f"Map saved as: {map_filename}")
