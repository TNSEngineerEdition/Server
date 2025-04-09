import json
import pickle
from pathlib import Path
from zipfile import ZipFile

import networkx as nx
import overpy
import pytest
from pyproj import Geod
from src.model import CityConfiguration, GTFSPackage
from src.tram_stop_mapper import TramStopMapper
from src.tram_track_graph_transformer.exceptions import (
    NodeNotFoundError,
    NoPathFoundError,
    PathTooLongError,
)
from src.tram_track_graph_transformer.tram_track_graph_transformer import (
    TramTrackGraphTransformer,
)

ASSETS = Path(__file__).parents[1] / "assets"
BASE_GRAPH_DATA = ASSETS / "tram_stop_reachability" / "base_graph_full_krakow.pickle"
TRAM_STOP_REACHABILITY_FILES = ASSETS / "tram_stop_reachability"
KRAKOW_CONFIG = Path(__file__).parents[2] / "config" / "cities" / "krakow.json"
TRAM_STOP_MAPPING_FILE = ASSETS / "tram_stop_mapping" / "2025-03-01T20-02-24.zip"


class TestTramStopGraphReachability:

    FILES_WITH_NO_PATH = [
        "Biprostal02_Urzednicza02.zip",
        "PlacWszystkichSwietych01_Filharmonia01.zip",
    ]
    FILES_WITH_TOO_LONG_PATHS = [
        "Lubicz02_UniwersytetEkonomiczny01.zip",
        "TeatrBagatela03_StaryKleparz02.zip",
    ]
    FILES_WITH_NO_NODE = [
        "UKEN_02.zip",
        "TeatrVariete_02.zip",
    ]

    @staticmethod
    def _load_base_graph():
        with open(BASE_GRAPH_DATA, "rb") as f:
            graph = pickle.load(f)

        return graph

    # to bedzie do usuniecia, konfiguracje biore z gotowego configa/przerobienia
    @staticmethod
    def _load_config(path: Path):
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return (
            config["max_distance_ratio"],
            {
                (p["from"], p["to"], p["ratio"])
                for p in config["custom_tram_stop_pair_max_distance_checks"]
            },
        )

    @staticmethod
    def _load_test_data(file_name: str):
        with ZipFile(TRAM_STOP_REACHABILITY_FILES / file_name) as zip_file:
            with zip_file.open("graph.pickle") as f:
                graph = pickle.load(f)
            with zip_file.open("expected_error_message.txt") as f:
                message = f.read().decode().strip()
            with zip_file.open("nodes.txt") as f:
                start, end = map(int, f.read().decode().strip().split(","))
        return graph, message, (start, end)

    def _get_tram_stop_mapping_data(self, zip_file: ZipFile):
        with zip_file.open("city_configuration.pickle") as file:
            city_configuration: CityConfiguration = pickle.load(file)

        with zip_file.open("gtfs_package.pickle") as file:
            gtfs_package: GTFSPackage = pickle.load(file)

        with zip_file.open("osm_relations_and_stops.pickle") as file:
            osm_relations_and_stops: overpy.Result = pickle.load(file)

        return (
            city_configuration,
            gtfs_package,
            osm_relations_and_stops,
        )

    def _get_tram_stop_pairs(self):
        with ZipFile(TRAM_STOP_MAPPING_FILE) as zip_file:
            city_configuration, gtfs_package, osm_relations_and_stops = (
                self._get_tram_stop_mapping_data(zip_file)
            )

        mapper = TramStopMapper(
            city_configuration=city_configuration,
            gtfs_package=gtfs_package,
            osm_relations_and_stops=osm_relations_and_stops,
        )

        mapped_stops = mapper.get_stop_nodes_by_gtfs_trip_id()
        tram_stop_pairs = set()
        for way in mapped_stops.values():
            for i in range(len(way) - 1):
                tram_stop_pairs.add((way[i], way[i + 1]))
        return tram_stop_pairs

    def _dijkstra_path(self, graph, start, end):
        geod = Geod(ellps="WGS84")
        return nx.dijkstra_path(
            graph,
            start,
            end,
            weight=lambda u, v, _: geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def test_graph_reachability(self):
        graph = self._load_base_graph()
        pairs = self._get_tram_stop_pairs()
        max_ratio, special_pairs = self._load_config(KRAKOW_CONFIG)
        custom_nodes_dict = {
            (start, end): ratio for (start, end, ratio) in special_pairs
        }
        for start_id, end_id in pairs:
            if end_id == 3114829955:
                end_id = 2375524420
            ratio = custom_nodes_dict.get((start_id, end_id), max_ratio)
            TramTrackGraphTransformer.check_path_viability(
                graph, start_id, end_id, ratio
            )

    @pytest.mark.parametrize("file_name", FILES_WITH_NO_NODE + FILES_WITH_NO_PATH)
    def test_graph_unreachability(self, file_name: str):
        max_ratio, special_pairs = self._load_config(KRAKOW_CONFIG)
        graph, expected_msg, (start_id, end_id) = self._load_test_data(file_name)
        custom_nodes_dict = {
            (start, end): ratio for (start, end, ratio) in special_pairs
        }
        ratio = custom_nodes_dict.get((start_id, end_id), max_ratio)

        with pytest.raises(
            (NodeNotFoundError, NoPathFoundError, PathTooLongError)
        ) as exc_info:
            TramTrackGraphTransformer.check_path_viability(
                graph, start_id, end_id, ratio
            )

        assert str(exc_info.value).strip() == expected_msg

    def test_astar_returns_same_path_as_dijkstra(self):
        graph = self._load_base_graph()
        nodes_by_id = {node.id: node for node in graph.nodes}
        pairs = self._get_tram_stop_pairs()
        for start_id, end_id in pairs:
            if end_id == 3114829955:
                end_id = 2375524420
            start, end = nodes_by_id[start_id], nodes_by_id[end_id]
            dijkstra_path = self._dijkstra_path(graph, start, end)
            astar_path = TramTrackGraphTransformer.shortest_path_between_nodes(
                graph, start, end
            )

            assert astar_path == dijkstra_path
