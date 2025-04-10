import json
import pickle

import networkx as nx
import overpy
import pytest
from src.model.city_configuration import CityConfiguration


@pytest.fixture
def relations_and_stops_overpass_query_result() -> overpy.Result:
    with open(
        "tests/assets/relations_and_stops_overpass_query_result.pickle", "rb"
    ) as file:
        return pickle.load(file)


@pytest.fixture
def krakow_tram_network_graph() -> nx.DiGraph:
    with open("tests/assets/krakow_tram_network_graph.pickle", "rb") as file:
        return pickle.load(file)


@pytest.fixture
def tram_trips_by_id() -> dict[str, list[int]]:
    with open("tests/assets/tram_trips_by_id.json") as file:
        return json.load(file)


@pytest.fixture
def krakow_city_configuration():
    with open("tests/assets/krakow_city_configuration.json") as file:
        return CityConfiguration.model_validate_json(file.read())
