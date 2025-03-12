import json

import networkx as nx


class NetworkGraph:
    def __init__(self, ways_file, stops_file):
        self.graph = nx.DiGraph()
        try:
            with open(ways_file, "r", encoding="utf-8") as f:
                self.ways = json.load(f)
            with open(stops_file, "r", encoding="utf-8") as f:
                self.stops = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading files: {e}")

        self.main_nodes = []

    def find_main_nodes(self):
        result = [
            stop["id"]
            for stop in self.stops
            if stop["id"] in self.graph.nodes
            and (
                self.graph.out_degree(stop["id"]) > 0
                or self.graph.in_degree(stop["id"]) > 0
            )
        ]

        for node in self.graph.nodes:
            if self.graph.in_degree(node) > 1 or self.graph.out_degree(node) > 1:
                result.append(node)

        return result

    def create_graph(self):
        for way in self.ways:
            nodes = way["nodes"]
            for i in range(len(nodes) - 1):
                self.graph.add_edge(nodes[i], nodes[i + 1])
        self.main_nodes = self.find_main_nodes()
        self.remove_unnecessary_nodes()

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

        return self.graph

    def map_graph_edges_to_localization(self):
        node_location = {}

        for way in self.ways:
            for node in way["nodes"]:
                if node not in node_location:
                    node_location[node] = (way["lat"], way["lon"])


g = NetworkGraph("tram_ways.json", "tram_stops.json")
g.create_graph()
