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
        graph = transformer.densify_graph_by_max_distance(25.0)

        for node_id in osm_tram_track_crossings.get_node_ids():

            # Assert
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
        graph = transformer.densify_graph_by_max_distance(25.0)

        for node_id in osm_tram_track_crossings.get_node_ids():

            # Assert
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
        graph = transformer.densify_graph_by_max_distance(25.0)

        for node_id in osm_tram_stops.get_node_ids():

            # Assert
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
        tolerance = max_densification_distance * 0.001

        # Act
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

                    # Assert
                    assert distance <= (max_densification_distance + tolerance)

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
        m = 0.05

        # Act
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

                # Assert
                assert sigma < mean * m

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
        with pytest.raises(ValueError) as Actual_error:
            transformer.densify_graph_by_max_distance(max_densification_distance)

        # Assert
        assert (
            str(Actual_error.value) == "max_distance_in_meters must be greater than 0."
        )
