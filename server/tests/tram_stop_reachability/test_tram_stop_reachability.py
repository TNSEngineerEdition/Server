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
from tests.constants import FROZEN_DATA_DIRECTORY

TRAM_STOP_REACHABILITY_DATA = (
    Path(__file__).parents[1] / "assets" / "tram_stop_reachability"
)
FULL_TRAM_NETWORK_GRAPH_DATA = (
    TRAM_STOP_REACHABILITY_DATA / "full_tram_network_graph.pickle"
)
# TRAM_STOP_REACHABILITY_FILES = ASSETS / "tram_stop_reachability"
TRAM_STOP_MAPPING_FILE = FROZEN_DATA_DIRECTORY / "2025-03-01T20-02-24.zip"


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
    def _full_tram_network_graph():
        with open(FULL_TRAM_NETWORK_GRAPH_DATA, "rb") as f:
            graph = pickle.load(f)

        return graph

    @staticmethod
    def _load_test_data(file_name: str):
        with ZipFile(TRAM_STOP_REACHABILITY_DATA / file_name) as zip_file:
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
        with ZipFile(TRAM_STOP_MAPPING_FILE) as zip_file:
            city_configuration, _, _ = self._get_tram_stop_mapping_data(zip_file)
        graph = self._full_tram_network_graph()
        pairs = self._get_tram_stop_pairs()
        max_ratio = city_configuration.max_distance_ratio
        custom_nodes_dict = {
            (item.from_, item.to): item.ratio
            for item in city_configuration.custom_tram_stop_pair_max_distance_checks
        }

        for start_id, end_id in pairs:
            ratio = custom_nodes_dict.get((start_id, end_id), max_ratio)
            TramTrackGraphTransformer.check_path_viability(
                graph, start_id, end_id, ratio
            )

    @pytest.mark.parametrize(
        "file_name", FILES_WITH_NO_NODE + FILES_WITH_NO_PATH + FILES_WITH_TOO_LONG_PATHS
    )
    def test_graph_unreachability(self, file_name: str):
        with ZipFile(TRAM_STOP_MAPPING_FILE) as zip_file:
            city_configuration, _, _ = self._get_tram_stop_mapping_data(zip_file)
        graph, expected_msg, (start_id, end_id) = self._load_test_data(file_name)
        max_ratio = city_configuration.max_distance_ratio
        custom_nodes_dict = {
            (item.from_, item.to): item.ratio
            for item in city_configuration.custom_tram_stop_pair_max_distance_checks
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
        graph = self._full_tram_network_graph()
        nodes_by_id = {node.id: node for node in graph.nodes}
        pairs = self._get_tram_stop_pairs()
        for start_id, end_id in pairs:
            start, end = nodes_by_id[start_id], nodes_by_id[end_id]
            dijkstra_path = self._dijkstra_path(graph, start, end)
            astar_path = TramTrackGraphTransformer.shortest_path_between_nodes(
                graph, start, end
            )

            assert astar_path == dijkstra_path
