import json
import pickle
from pathlib import Path
from zipfile import ZipFile

import networkx as nx
import pytest
from networkx.exception import NetworkXNoPath
from pyproj import Geod
from src.tram_track_graph_transformer.exceptions import (
    NoPathFoundError,
    PathTooLongError,
)
from src.tram_track_graph_transformer.node_type import NodeType

ASSETS = Path(__file__).parents[1] / "assets" / "tram_stop_reachability"
BASE_GRAPH_DATA = ASSETS / "base_graph_data.zip"
KRAKOW_CONFIG = Path(__file__).parents[2] / "config" / "cities" / "krakow.json"


class TestTramStopGraphReachability:
    FILES_WITH_NO_PATH = [
        "PlacWszystkichSwietych_Filharmonia.zip",
        "Biprostal02_Urzednicza02.zip",
    ]
    FILES_WITH_TOO_LONG_PATHS = [
        "TeatrBagatela03_StaryKleparz02.zip",
        "Lubicz02_UniwersytetEkonomiczny01.zip",
    ]
    geod = Geod(ellps="WGS84")

    @staticmethod
    def _load_base_data():
        with ZipFile(BASE_GRAPH_DATA) as zip_file:
            with zip_file.open("basic_graph.pkl") as f:
                graph = pickle.load(f)
            with zip_file.open("tram_stop_pairs_distances.pkl") as f:
                distances = pickle.load(f)
            nodes = {
                node.id: node for node in graph.nodes if node.type == NodeType.TRAM_STOP
            }
        return graph, nodes, distances

    @staticmethod
    def _load_config(path: Path):
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return (
            config["max_distance_ratio"],
            config["special_max_distance_ratio"],
            {(p["from"], p["to"]) for p in config["special_tram_stop_pairs"].values()},
        )

    @staticmethod
    def _load_test_data(file_name: str):
        with ZipFile(ASSETS / file_name) as zip_file:
            with zip_file.open("graph.pkl") as f:
                graph = pickle.load(f)
            with zip_file.open("expected_error_message.txt") as f:
                message = f.read().decode().strip()
            with zip_file.open("nodes.txt") as f:
                start, end = map(int, f.read().decode().strip().split(","))
        return graph, message, (start, end)

    def _shortest_path(self, graph, start, end):
        return nx.astar_path(
            graph,
            start,
            end,
            heuristic=lambda u, v: self.geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
            weight=lambda u, v, d: self.geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def _path_distance(self, path):
        lons = [node.lon for node in path]
        lats = [node.lat for node in path]
        return self.geod.line_length(lons, lats)

    def test_graph_reachability(self):
        graph, nodes_by_id, pairs = self._load_base_data()
        max_ratio, special_ratio, special_pairs = self._load_config(KRAKOW_CONFIG)

        for (start_id, end_id), simple_dist in pairs.items():
            path = self._shortest_path(
                graph, nodes_by_id[start_id], nodes_by_id[end_id]
            )
            actual = self._path_distance(path)
            limit = simple_dist * (
                special_ratio if (start_id, end_id) in special_pairs else max_ratio
            )

            # Small tolerance added to account for floating point precision errors,
            # which may occur even for very short paths
            assert actual + 1e-6 >= simple_dist

            if actual > limit:
                raise PathTooLongError(start_id, end_id, actual, limit)

    @pytest.mark.parametrize("file_name", FILES_WITH_NO_PATH)
    def test_no_path_found(self, file_name: str):
        graph, expected_msg, (start_id, end_id) = self._load_test_data(file_name)
        _, nodes_by_id, _ = self._load_base_data()

        start, end = nodes_by_id[start_id], nodes_by_id[end_id]

        with pytest.raises(NoPathFoundError) as exc_info:
            try:
                self._shortest_path(graph, start, end)
            except NetworkXNoPath:
                raise NoPathFoundError(start, end)
        assert str(exc_info.value).strip() == expected_msg

    @pytest.mark.parametrize("file_name", FILES_WITH_TOO_LONG_PATHS)
    def test_path_too_long(self, file_name: str):
        graph, expected_msg, (start_id, end_id) = self._load_test_data(file_name)
        _, nodes_by_id, pairs = self._load_base_data()
        max_ratio, special_ratio, special_pairs = self._load_config(KRAKOW_CONFIG)

        start, end = nodes_by_id[start_id], nodes_by_id[end_id]
        simple = pairs[(start_id, end_id)]
        actual = self._path_distance(self._shortest_path(graph, start, end))
        allowed = simple * (
            special_ratio if (start_id, end_id) in special_pairs else max_ratio
        )

        with pytest.raises(PathTooLongError) as exc_info:
            if actual <= allowed:
                pytest.fail("Expected PathTooLongError, but distance was acceptable.")
            raise PathTooLongError(start_id, end_id, actual, allowed)

        assert str(exc_info.value).strip() == expected_msg
