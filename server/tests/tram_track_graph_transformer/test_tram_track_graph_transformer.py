import json
import pickle
from math import ceil
from pathlib import Path

import pytest
from src.overpass_client import OverpassClient
from src.tram_track_graph_transformer import TramTrackGraphTransformer
from src.tram_track_graph_transformer.node import Node

TRAM_TRACK_GRAPH_TRANSFORMER_DIRECTORY = (
    Path(__file__).parents[1] / "assets" / "tram_track_graph_transformer"
)


@pytest.fixture(scope="module")
def graph_25():
    tram_stops_and_tracks = OverpassClient.get_tram_stops_and_tracks("Kraków")
    transformer = TramTrackGraphTransformer(tram_stops_and_tracks)
    return transformer.densify_graph_by_max_distance(25.0)


class TestTramTrackGraphTransformer:
    CORRECT_MAX_INTERPOLATION_DISTANCES = [10.0, 25.0]
    INCORRECT_MAX_INTERPOLATION_DISTANCES = [-5.0, 0.0]

    def _get_tram_tracks_crossings_data(self) -> dict[str, Node]:
        with open(
            TRAM_TRACK_GRAPH_TRANSFORMER_DIRECTORY
            / "tram_track_crossings_query_results.pickle",
            "rb",
        ) as pickle_file:
            tram_track_crossings_nodes: dict[str, Node] = pickle.load(pickle_file)
        return tram_track_crossings_nodes

    def _get_correct_tram_track_interpolation(self) -> dict:
        with open(
            TRAM_TRACK_GRAPH_TRANSFORMER_DIRECTORY
            / "correct_tram_track_interpolation.json",
            "r",
        ) as json_file:
            correct_tram_track_interpolation: dict = json.load(json_file)
        return correct_tram_track_interpolation

    def _is_reachable_within_depth(
        self, graph, current: Node, goal: Node, step: int, max_steps: int, forward=True
    ):
        if goal == current:
            return {"is_reachable": True, "steps": step}
        if step == max_steps:
            return {"is_reachable": False, "steps": step, "last_node": current}
        if forward:
            successors = list(graph.successors(current))
            for succ in successors:
                result = self._is_reachable_within_depth(
                    graph, current=succ, goal=goal, step=step + 1, max_steps=max_steps
                )
                if result["is_reachable"]:
                    return result
            return result
        predecessors = list(graph.predecessors(current))
        for pred in predecessors:
            result = self._is_reachable_within_depth(
                graph,
                current=pred,
                goal=goal,
                step=step + 1,
                max_steps=max_steps,
                forward=False,
            )
            if result["is_reachable"]:
                return result
        return result

    def test_tram_track_crossings_neighbors_amount(self, graph_25):
        # prepare data
        tram_track_crossings_nodes = self._get_tram_tracks_crossings_data()

        # assert
        for crossing_node in tram_track_crossings_nodes.values():
            if graph_25.has_node(crossing_node):
                assert len(list(graph_25.predecessors(crossing_node))) == len(
                    list(graph_25.successors(crossing_node))
                )

    @pytest.mark.parametrize(
        "max_interpolation_distance", CORRECT_MAX_INTERPOLATION_DISTANCES
    )
    def test_interpolation(self, max_interpolation_distance: int):
        # make graph
        tram_stops_and_tracks = OverpassClient.get_tram_stops_and_tracks("Kraków")
        transformer = TramTrackGraphTransformer(tram_stops_and_tracks)
        graph = transformer.densify_graph_by_max_distance(max_interpolation_distance)

        # prepare data
        correct_tram_track_interpolation: dict = (
            self._get_correct_tram_track_interpolation()
        )

        for test_name, test_data in correct_tram_track_interpolation.items():
            expected_steps = test_data["distance"] // max_interpolation_distance + 1
            tolerance = ceil(expected_steps * 0.03)

            result = self._is_reachable_within_depth(
                graph=graph,
                current=transformer._nodes_by_id[test_data["start_node_id"]],
                goal=transformer._nodes_by_id[test_data["goal_node_id"]],
                step=0,
                max_steps=expected_steps + tolerance,
            )

            assert_msg = (
                f"Test case '{test_name}' failed: "
                f"start={test_data["start_node_id"]}, goal={test_data["goal_node_id"]}, "
                f"expected_steps={expected_steps} +/- {tolerance}, actual_steps={result["steps"]}"
            )

            # assert
            assert result["is_reachable"] is True, assert_msg
            assert (
                result["steps"] >= expected_steps - tolerance
                and result["steps"] <= expected_steps + tolerance
            ), assert_msg

    @pytest.mark.parametrize(
        "max_interpolation_distance", INCORRECT_MAX_INTERPOLATION_DISTANCES
    )
    def test_interpolation_distance_exception(self, max_interpolation_distance: int):
        # make graph
        tram_stops_and_tracks = OverpassClient.get_tram_stops_and_tracks("Kraków")
        transformer = TramTrackGraphTransformer(tram_stops_and_tracks)

        # prepare error
        with pytest.raises(ValueError) as actual_error:
            transformer.densify_graph_by_max_distance(max_interpolation_distance)

        # assert
        assert (
            str(actual_error.value) == "max_distance_in_meters must be greater than 0."
        )
