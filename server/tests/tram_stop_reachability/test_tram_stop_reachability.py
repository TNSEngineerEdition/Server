import networkx as nx
import pytest
from pyproj import Geod
from src.model import CityConfiguration
from src.tram_track_graph_transformer import (
    Node,
    NodeNotFoundError,
    NoPathFoundError,
    PathTooLongError,
    TramTrackGraphInspector,
)


class TestTramStopGraphReachability:

    @pytest.fixture
    def tram_stop_pairs(self, tram_trips_by_id: dict[str, list[int]]):
        return {
            (stop_ids[i], stop_ids[i + 1])
            for stop_ids in tram_trips_by_id.values()
            for i in range(len(stop_ids) - 1)
        }

    def _get_dijkstra_path(self, graph: nx.DiGraph, start_node: Node, end_node: Node):
        geod = Geod(ellps="WGS84")
        return nx.dijkstra_path(
            graph,
            start_node,
            end_node,
            weight=lambda u, v, _: geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def test_check_path_viability(
        self,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: nx.DiGraph,
        tram_stop_pairs: set[tuple[int, int]],
    ):
        # Arrange
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        for start_id, end_id in tram_stop_pairs:
            tram_graph_inspector.check_path_viability(
                start_id,
                end_id,
                krakow_city_configuration.custom_tram_stop_pair_ratio_map.get(
                    (start_id, end_id), krakow_city_configuration.max_distance_ratio
                ),
            )

    @pytest.mark.parametrize(
        "node_id",
        [
            pytest.param(2419986542, id="node_not_found_2419986542"),
            pytest.param(2419986544, id="node_not_found_2419986544"),
            pytest.param(651848336, id="node_not_found_651848336"),
        ],
    )
    def test_check_path_viability_node_not_found(
        self,
        node_id,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: nx.DiGraph,
        tram_stop_pairs: set[tuple[int, int]],
    ):
        # Arrange
        krakow_tram_network_graph.remove_node(node_id)
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(NodeNotFoundError) as exc_info:
            for start_id, end_id in tram_stop_pairs:
                tram_graph_inspector.check_path_viability(
                    start_id,
                    end_id,
                    krakow_city_configuration.custom_tram_stop_pair_ratio_map.get(
                        (start_id, end_id), krakow_city_configuration.max_distance_ratio
                    ),
                )

        # Assert
        assert (
            str(exc_info.value).strip()
            == f"Node with id {node_id} not found in the graph."
        )

    @pytest.mark.parametrize(
        ("edge", "start_stop", "end_stop"),
        [
            pytest.param(
                (6738229788, 6738229790),
                2419959769,
                2420069703,
                id="path_too_long_6738229788_to_6738229790",
            ),
            pytest.param(
                (2420200294, 8551858404),
                2420200261,
                2420233975,
                id="path_too_long_2420200294_to_8551858404",
            ),
            pytest.param(
                (2419367476, 8551888613),
                11271425380,
                2419894822,
                id="path_too_long_2419367476_to_8551888613",
            ),
        ],
    )
    def test_check_path_viability_path_too_long(
        self,
        edge,
        start_stop,
        end_stop,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: nx.DiGraph,
        tram_stop_pairs: set[tuple[int, int]],
    ):
        # Arrange
        krakow_tram_network_graph.remove_edge(*edge)
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(PathTooLongError) as exc_info:
            for start_id, end_id in tram_stop_pairs:
                tram_graph_inspector.check_path_viability(
                    start_id,
                    end_id,
                    krakow_city_configuration.custom_tram_stop_pair_ratio_map.get(
                        (start_id, end_id), krakow_city_configuration.max_distance_ratio
                    ),
                )

        # Assert
        assert (
            str(exc_info.value)
            .strip()
            .startswith(f"Path too long: {start_stop} -> {end_stop}")
        )

    @pytest.mark.parametrize(
        ("edge", "start_stop", "end_stop"),
        [
            pytest.param(
                (12685345137, 12685345138),
                1768224703,
                1768224656,
                id="no_path_found_12685345137_to_12685345138",
            ),
            pytest.param(
                (12685345293, 12685345294),
                2420286331,
                2423789750,
                id="no_path_found_12685345293_to_12685345294",
            ),
            pytest.param(
                (12685341641, 12685341642),
                2419986545,
                2419986538,
                id="no_path_found_12685341641_to_12685341642",
            ),
        ],
    )
    def test_check_path_viability_no_path_found(
        self,
        edge,
        start_stop,
        end_stop,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: nx.DiGraph,
        tram_stop_pairs: set[tuple[int, int]],
    ):
        # Arrange
        krakow_tram_network_graph.remove_edge(*edge)
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(NoPathFoundError) as exc_info:
            for start_id, end_id in tram_stop_pairs:
                tram_graph_inspector.check_path_viability(
                    start_id,
                    end_id,
                    krakow_city_configuration.custom_tram_stop_pair_ratio_map.get(
                        (start_id, end_id), krakow_city_configuration.max_distance_ratio
                    ),
                )

        # Assert
        assert (
            str(exc_info.value).strip()
            == f"No path found between stops: {start_stop} -> {end_stop}"
        )

    def test_shortest_path_between_nodes(
        self,
        krakow_tram_network_graph: nx.DiGraph,
        tram_stop_pairs: set[tuple[int, int]],
    ):
        # Arrange
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)
        nodes_by_id = {node.id: node for node in krakow_tram_network_graph.nodes}
        for start_id, end_id in tram_stop_pairs:
            dijkstra_path = self._get_dijkstra_path(
                krakow_tram_network_graph, nodes_by_id[start_id], nodes_by_id[end_id]
            )

            # Act
            astar_path = tram_graph_inspector.shortest_path_between_nodes(
                nodes_by_id[start_id], nodes_by_id[end_id]
            )

            # Assert
            assert astar_path == dijkstra_path
