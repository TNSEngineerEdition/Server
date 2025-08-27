import networkx as nx
import pytest
from pyproj import Geod

from city_data_builder import CityConfiguration
from tram_track_graph_transformer import (
    Node,
    NodeNotFoundError,
    NoPathFoundError,
    PathTooLongError,
    TramTrackGraphInspector,
)


class TestTramTrackGraphInspector:
    geod = Geod(ellps="WGS84")

    @pytest.fixture
    def unique_tram_stop_pairs(
        self, tram_trips_by_id: dict[str, list[int]]
    ) -> set[tuple[int, int]]:
        return TramTrackGraphInspector.get_unique_tram_stop_pairs(tram_trips_by_id)

    def _get_dijkstra_path(
        self, graph: "nx.DiGraph[Node]", start_node: Node, end_node: Node
    ) -> list[Node]:
        return nx.dijkstra_path(
            graph,
            start_node,
            end_node,
            weight=lambda u, v, _: self.geod.inv(u.lon, u.lat, v.lon, v.lat)[2],
        )

    def test_get_unique_tram_stop_pairs(
        self, tram_trips_by_id: dict[str, list[int]]
    ) -> None:
        # Act
        unique_tram_stop_pairs = TramTrackGraphInspector.get_unique_tram_stop_pairs(
            tram_trips_by_id
        )

        # Assert
        assert len(unique_tram_stop_pairs) == 442
        assert all(
            (dest, source) not in unique_tram_stop_pairs
            for source, dest in unique_tram_stop_pairs
        )

    def test_check_path_viability(
        self,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: "nx.DiGraph[Node]",
        unique_tram_stop_pairs: set[tuple[int, int]],
    ) -> None:
        # Arrange
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        for start_id, end_id in unique_tram_stop_pairs:
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
            pytest.param(2419986542, id="Glowackiego 02"),
            pytest.param(2419986544, id="UKEN 02"),
            pytest.param(651848336, id="Rondo Mogilskie 05"),
        ],
    )
    def test_check_path_viability_node_not_found(
        self,
        node_id: int,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: "nx.DiGraph[Node]",
        unique_tram_stop_pairs: set[tuple[int, int]],
    ) -> None:
        # Arrange
        krakow_tram_network_graph.remove_node(node_id)  # type: ignore
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(NodeNotFoundError) as exc_info:
            for start_id, end_id in unique_tram_stop_pairs:
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
                id="Teatr Bagatela 03 -> Stary Kleparz 02",
            ),
            pytest.param(
                (2420200294, 8551858404),
                2420200261,
                2420233975,
                id="Lubicz 02 -> Uniwersytet Ekonomiczny 01",
            ),
            pytest.param(
                (2419367476, 8551888613),
                11271425380,
                2419894822,
                id="UJ / AST 02 -> Teatr Bagatela 01",
            ),
        ],
    )
    def test_check_path_viability_path_too_long(
        self,
        edge: tuple[int, int],
        start_stop: int,
        end_stop: int,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: "nx.DiGraph[Node]",
        unique_tram_stop_pairs: set[tuple[int, int]],
    ) -> None:
        # Arrange
        krakow_tram_network_graph.remove_edge(*edge)  # type: ignore
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(PathTooLongError) as exc_info:
            for start_id, end_id in unique_tram_stop_pairs:
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
                id="Bialucha 02 -> Cystersow 02",
            ),
            pytest.param(
                (12685345293, 12685345294),
                2420286331,
                2423789750,
                id="Nowy Kleparz 02 -> Pedzichow 02",
            ),
            pytest.param(
                (12685341641, 12685341642),
                2419986545,
                2419986538,
                id="Urzednicza 01 -> Biprostal 01",
            ),
        ],
    )
    def test_check_path_viability_no_path_found(
        self,
        edge: tuple[int, int],
        start_stop: int,
        end_stop: int,
        krakow_city_configuration: CityConfiguration,
        krakow_tram_network_graph: "nx.DiGraph[Node]",
        unique_tram_stop_pairs: set[tuple[int, int]],
    ) -> None:
        # Arrange
        krakow_tram_network_graph.remove_edge(*edge)  # type: ignore
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)

        # Act
        with pytest.raises(NoPathFoundError) as exc_info:
            for start_id, end_id in unique_tram_stop_pairs:
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
        krakow_tram_network_graph: "nx.DiGraph[Node]",
        unique_tram_stop_pairs: set[tuple[int, int]],
    ) -> None:
        # Arrange
        tram_graph_inspector = TramTrackGraphInspector(krakow_tram_network_graph)
        nodes_by_id = {node.id: node for node in krakow_tram_network_graph.nodes}
        for start_id, end_id in unique_tram_stop_pairs:
            dijkstra_path = self._get_dijkstra_path(
                krakow_tram_network_graph, nodes_by_id[start_id], nodes_by_id[end_id]
            )

            # Act
            astar_path = tram_graph_inspector.shortest_path_between_nodes(
                nodes_by_id[start_id], nodes_by_id[end_id]
            )

            # Assert
            assert astar_path == dijkstra_path
