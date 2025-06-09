from collections import deque
from math import sqrt

import overpy
import pytest
from pyproj import Geod

from src.tram_track_graph_transformer import Node, TramTrackGraphTransformer


class TestTramTrackGraphTransformer:
    CORRECT_MAX_DENSIFICATION_DISTANCES = [10.0, 25.0]
    INCORRECT_MAX_DENSIFICATION_DISTANCES = [-5.0, 0.0]
    _geod = Geod(ellps="WGS84")

    def _assert_densified_edges_within_distance(self, graph, perm_nodes, max_distance):
        tolerance = max_distance * 0.001
        for perm_node in perm_nodes:
            queue: deque[Node] = deque()
            queue.append(perm_node)
            visited = set()

            while queue:
                current = queue.popleft()
                visited.add(current)

                for neighbor in graph.successors(current):
                    if neighbor not in perm_nodes and neighbor not in visited:
                        queue.append(neighbor)

                    _, _, distance = self._geod.inv(
                        current.lon, current.lat, neighbor.lon, neighbor.lat
                    )
                    assert distance <= (max_distance + tolerance)

    def _assert_even_spacing_of_densified_nodes(self, graph, perm_nodes):
        m = 0.05
        for perm_node in perm_nodes:
            succ_nodes = graph.successors(perm_node)

            for succ_node in succ_nodes:
                if succ_node in perm_nodes:
                    continue

                distances = []
                prev_node = perm_node
                next_node = succ_node
                visited = {prev_node}

                while next_node not in perm_nodes and next_node not in visited:
                    _, _, distance = self._geod.inv(
                        prev_node.lon, prev_node.lat, next_node.lon, next_node.lat
                    )
                    distances.append(distance)
                    visited.add(prev_node)
                    prev_node = next_node
                    next_node = list(graph.successors(prev_node))[0]

                if not distances:
                    continue

                mean = sum(distances) / len(distances)
                sigma = sqrt(sum((x - mean) ** 2 for x in distances) / len(distances))
                assert sigma < mean * m

    def test_tram_track_transformer_crossings_in_graph(
        self,
        osm_tram_track_crossings: overpy.Result,
        tram_stops_and_tracks_overpass_query_result,
        krakow_city_configuration,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )

        # Act
        graph = transformer.densify_graph_by_max_distance(25.0)

        # Assert
        for node_id in osm_tram_track_crossings.get_node_ids():
            assert graph.has_node(node_id)

    def test_tram_track_transformer_crossings_neighbors_amount(
        self,
        osm_tram_track_crossings: overpy.Result,
        tram_stops_and_tracks_overpass_query_result,
        krakow_city_configuration,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )

        # Act
        graph = transformer.densify_graph_by_max_distance(25.0)

        # Assert
        for node_id in osm_tram_track_crossings.get_node_ids():
            assert len(list(graph.predecessors(node_id))) == len(
                list(graph.successors(node_id))
            )

    def test_tram_track_transformer_tram_stops_in_graph(
        self,
        osm_tram_stops: overpy.Result,
        tram_stops_and_tracks_overpass_query_result,
        krakow_city_configuration,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )

        # Act
        graph = transformer.densify_graph_by_max_distance(25.0)

        # Assert
        for node_id in osm_tram_stops.get_node_ids():
            assert graph.has_node(node_id)

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_tram_track_transformer_densify_max_distance(
        self,
        max_densification_distance: float,
        tram_stops_and_tracks_overpass_query_result,
        krakow_city_configuration,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )
        perm_nodes = transformer.permament_nodes

        # Act
        densified_graph = transformer.densify_graph_by_max_distance(
            max_densification_distance
        )

        # Assert
        self._assert_densified_edges_within_distance(
            densified_graph, perm_nodes, max_densification_distance
        )

    @pytest.mark.parametrize(
        "max_densification_distance", CORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_tram_track_transformer_densify_even_spacing(
        self,
        max_densification_distance: float,
        tram_stops_and_tracks_overpass_query_result,
        krakow_city_configuration,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )
        perm_nodes = transformer.permament_nodes

        # Act
        densified_graph = transformer.densify_graph_by_max_distance(
            max_densification_distance
        )

        # Assert
        self._assert_even_spacing_of_densified_nodes(densified_graph, perm_nodes)

    @pytest.mark.parametrize(
        "max_densification_distance", INCORRECT_MAX_DENSIFICATION_DISTANCES
    )
    def test_tram_track_transformer_densify_exception(
        self,
        max_densification_distance: float,
        krakow_city_configuration,
        tram_stops_and_tracks_overpass_query_result: overpy.Result,
    ):
        # Arrange
        transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks_overpass_query_result, krakow_city_configuration
        )

        # Act
        with pytest.raises(ValueError) as exc:
            transformer.densify_graph_by_max_distance(max_densification_distance)

        # Assert
        assert str(exc.value) == "max_distance_in_meters must be greater than 0."
