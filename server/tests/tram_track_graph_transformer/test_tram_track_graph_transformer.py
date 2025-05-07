from collections import deque
from math import sqrt

import overpy
import pytest
from networkx import DiGraph
from pyproj import Geod
from src.tram_track_graph_transformer import TramTrackGraphTransformer
from src.tram_track_graph_transformer.node import Node


@pytest.fixture()
def graph_25(osm_tram_stops_and_tracks, krakow_city_configuration):
    transformer = TramTrackGraphTransformer(
        osm_tram_stops_and_tracks, krakow_city_configuration
    )
    return (transformer, transformer.densify_graph_by_max_distance(25.0))


class TestTramTrackGraphTransformer:
    CORRECT_MAX_DENSIFICATION_DISTANCES = [10.0, 25.0]
    INCORRECT_MAX_DENSIFICATION_DISTANCES = [-5.0, 0.0]
    _geod = Geod(ellps="WGS84")

    def test_tram_track_transformer_crossings_in_graph(
        self,
        krakow_ignored_crossings_and_stops,
        osm_tram_track_crossings: overpy.Result,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph],
    ):
        # arrange
        _, graph = graph_25

        for node_id in osm_tram_track_crossings.get_node_ids():
            if (
                node_id
                not in krakow_ignored_crossings_and_stops["ignored_crossings_ids"]
            ):

                # assert
                assert graph.has_node(node_id) is True

    def test_tram_track_transformer_crossings_neighbors_amount(
        self,
        krakow_ignored_crossings_and_stops,
        osm_tram_track_crossings: overpy.Result,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph],
    ):
        # arrange
        _, graph = graph_25

        for node_id in osm_tram_track_crossings.get_node_ids():
            if (
                node_id
                not in krakow_ignored_crossings_and_stops["ignored_crossings_ids"]
            ):

                # assert
                assert len(list(graph.predecessors(node_id))) == len(
                    list(graph.successors(node_id))
                )

    def test_tram_track_transformer_tram_stops_in_graph(
        self,
        krakow_ignored_crossings_and_stops,
        osm_tram_stops: overpy.Result,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph],
    ):
        # arrange
        _, graph = graph_25

        for node_id in osm_tram_stops.get_node_ids():
            if (
                node_id
                not in krakow_ignored_crossings_and_stops["ignored_tram_stops_ids"]
            ):

                # assert
                assert graph.has_node(node_id) is True

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_tram_track_transformer_densify_max_distance(
        self,
        max_densification_distance: float,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph],
    ):
        # arrange
        transformer, _ = graph_25
        perm_nodes = transformer.permament_nodes
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

                    _, _, distance = self._geod.inv(
                        prev_node.lon, prev_node.lat, next_node.lon, next_node.lat
                    )

                    # assert
                    assert distance <= (max_densification_distance + tolerance)

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_tram_track_transformer_densify_even_spacing(
        self,
        max_densification_distance: float,
        graph_25: tuple[TramTrackGraphTransformer, DiGraph],
    ):
        # arrange
        transformer, _ = graph_25
        perm_nodes = transformer.permament_nodes
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
                    _, _, distance = self._geod.inv(
                        prev_node.lon, prev_node.lat, next_node.lon, next_node.lat
                    )
                    distances.append(distance)
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
    def test_tram_track_transformer_densify_exception(
        self,
        max_densification_distance: float,
        krakow_city_configuration,
        osm_tram_stops_and_tracks: overpy.Result,
    ):
        # arrange
        transformer = TramTrackGraphTransformer(
            osm_tram_stops_and_tracks, krakow_city_configuration
        )

        # act
        with pytest.raises(ValueError) as actual_error:
            transformer.densify_graph_by_max_distance(max_densification_distance)

        # assert
        assert (
            str(actual_error.value) == "max_distance_in_meters must be greater than 0."
        )
