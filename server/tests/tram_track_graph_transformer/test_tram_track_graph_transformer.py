import pickle
from collections import deque
from math import sqrt
from zipfile import ZipFile

import overpy
import pytest
from geopy.distance import geodesic
from networkx import DiGraph
from src.model import CityConfiguration
from src.tram_track_graph_transformer import TramTrackGraphTransformer
from src.tram_track_graph_transformer.node import Node
from tests.constants import FROZEN_DATA_DIRECTORY

FILES_WITH_DATA = ["2025-04-22T03-35-34.zip"]


@pytest.fixture(scope="module", params=FILES_WITH_DATA)
def graph_25(request):
    file_path = request.param

    with ZipFile(FROZEN_DATA_DIRECTORY / file_path) as zip_file:
        with zip_file.open("osm_tram_stops_and_tracks.pickle") as file:
            osm_tram_stops_and_tracks: overpy.Result = pickle.load(file)

    transformer = TramTrackGraphTransformer(osm_tram_stops_and_tracks)
    return (transformer, transformer.densify_graph_by_max_distance(25.0), file_path)


class TestTramTrackGraphTransformer:
    CORRECT_MAX_DENSIFICATION_DISTANCES = [10.0, 25.0]
    INCORRECT_MAX_DENSIFICATION_DISTANCES = [-5.0, 0.0]

    def _get_city_configuration(self, zip_file: ZipFile) -> CityConfiguration:
        with zip_file.open("city_configuration.pickle") as file:
            city_configuration: CityConfiguration = pickle.load(file)
        return city_configuration

    def _get_tram_track_crossings_data(self, zip_file: ZipFile) -> overpy.Result:
        with zip_file.open("osm_tram_track_crossings.pickle") as file:
            osm_tram_track_crossings: overpy.Result = pickle.load(file)
        return osm_tram_track_crossings

    def _get_tram_stops_and_tracks_data(self, zip_file: ZipFile) -> overpy.Result:
        with zip_file.open("osm_tram_stops_and_tracks.pickle") as file:
            osm_tram_stops_and_tracks: overpy.Result = pickle.load(file)
        return osm_tram_stops_and_tracks

    def _get_tram_stops_data(self, zip_file: ZipFile) -> overpy.Result:
        with zip_file.open("osm_tram_stops.pickle") as file:
            osm_tram_stops: overpy.Result = pickle.load(file)
        return osm_tram_stops

    def test_if_tram_track_crossings_in_graph(
        self, graph_25: tuple[TramTrackGraphTransformer, DiGraph, str]
    ):
        # arrange
        transformer, graph, file_name = graph_25

        with ZipFile(FROZEN_DATA_DIRECTORY / file_name) as zip_file:
            city_configuration = self._get_city_configuration(zip_file)
            osm_tram_track_crossings = self._get_tram_track_crossings_data(zip_file)

        for node_id in osm_tram_track_crossings.get_node_ids():
            if node_id not in city_configuration.ignored_crossings_ids:

                # assert
                assert graph.has_node(transformer.get_node_by_id(node_id)) is True

    def test_tram_track_crossings_neighbors_amount(
        self, graph_25: tuple[TramTrackGraphTransformer, DiGraph, str]
    ):
        # arrange
        transformer, graph, file_name = graph_25

        with ZipFile(FROZEN_DATA_DIRECTORY / file_name) as zip_file:
            city_configuration = self._get_city_configuration(zip_file)
            osm_tram_track_crossings = self._get_tram_track_crossings_data(zip_file)

        for node_id in osm_tram_track_crossings.get_node_ids():
            if node_id not in city_configuration.ignored_crossings_ids:
                node = transformer.get_node_by_id(node_id)

                # assert
                assert len(list(graph.predecessors(node))) == len(
                    list(graph.successors(node))
                )

    def test_if_tram_stops_in_graph(
        self, graph_25: tuple[TramTrackGraphTransformer, DiGraph, str]
    ):
        # arrange
        transformer, graph, file_name = graph_25

        with ZipFile(FROZEN_DATA_DIRECTORY / file_name) as zip_file:
            city_configuration = self._get_city_configuration(zip_file)
            osm_tram_stops = self._get_tram_stops_data(zip_file)

        for node_id in osm_tram_stops.get_node_ids():
            if node_id not in city_configuration.ignored_tram_stops_ids:

                # assert
                assert graph.has_node(transformer.get_node_by_id(node_id)) is True

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_densification_max_distance(
        self,
        max_densification_distance: int,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph, str],
    ):
        # arrange
        transformer, _, _ = graph_25
        perm_nodes = transformer.get_permament_nodes()
        tolerance = max_densification_distance * 0.001

        # act
        densified_graph = transformer.densify_graph_by_max_distance(
            max_densification_distance
        )

        for perm_node in perm_nodes:
            prev_nodes: deque[Node] = deque()
            prev_nodes.append(perm_node)
            visited = set()

            while prev_nodes:
                prev_node = prev_nodes.popleft()
                visited.add(prev_node)

                for next_node in densified_graph.successors(prev_node):
                    if next_node not in perm_nodes and next_node not in visited:
                        prev_nodes.append(next_node)

                    distance = geodesic(
                        (prev_node.lat, prev_node.lon), (next_node.lat, next_node.lon)
                    ).meters

                    # assert
                    assert distance <= (max_densification_distance + tolerance)

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_densification_even_spacing(
        self,
        max_densification_distance: int,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph, str],
    ):
        # arrange
        transformer, _, _ = graph_25
        perm_nodes = transformer.get_permament_nodes()
        m = 0.05

        # act
        densified_graph = transformer.densify_graph_by_max_distance(
            max_densification_distance
        )

        for perm_node in perm_nodes:
            succ_nodes = densified_graph.successors(perm_node)

            for succ_node in succ_nodes:
                if succ_node in perm_nodes:
                    continue
                distances = []
                prev_node = perm_node
                next_node = succ_node
                visited = set()
                visited.add(prev_node)

                while next_node not in perm_nodes and next_node not in visited:
                    distances.append(
                        geodesic(
                            (prev_node.lat, prev_node.lon),
                            (next_node.lat, next_node.lon),
                        ).meters
                    )
                    visited.add(prev_node)
                    prev_node = next_node
                    next_node = list(densified_graph.successors(prev_node))[0]

                n = len(distances)
                if not n:
                    continue

                mean = sum(distances) / n
                squares_sum = sum(map(lambda x: (x - mean) ** 2, distances))
                sigma = sqrt(squares_sum / n)

                # assert
                assert sigma < mean * m

    @pytest.mark.parametrize(
        "max_densification_distance", INCORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_densification_distance_exception(
        self,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph, str],
        max_densification_distance: int,
    ):
        # arrange
        _, _, file_name = graph_25

        with ZipFile(FROZEN_DATA_DIRECTORY / file_name) as zip_file:
            tram_stops_and_tracks = self._get_tram_stops_and_tracks_data(zip_file)

        transformer = TramTrackGraphTransformer(tram_stops_and_tracks)

        # act
        with pytest.raises(ValueError) as actual_error:
            transformer.densify_graph_by_max_distance(max_densification_distance)

        # assert
        assert (
            str(actual_error.value) == "max_distance_in_meters must be greater than 0."
        )
