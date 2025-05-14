import json
import pickle
import zipfile
from pathlib import Path

import networkx as nx
import overpy
import pytest

from src.city_data_builder import CityConfiguration
from src.tram_stop_mapper import GTFSPackage


@pytest.fixture
def gtfs_package():
    return GTFSPackage.from_file("tests/assets/gtfs_schedule.zip")


@pytest.fixture
def relations_and_stops_overpass_query_result() -> overpy.Result:
    with zipfile.ZipFile(
        "tests/assets/relations_and_stops_overpass_query_result.zip"
    ) as zip_file:
        with zip_file.open("relations_and_stops_overpass_query_result.pickle") as file:
            return pickle.load(file)


@pytest.fixture
def tram_stops_and_tracks_overpass_query_result() -> overpy.Result:
    with zipfile.ZipFile(
        "tests/assets/tram_stops_and_tracks_overpass_query_result.zip"
    ) as zip_file:
        with zip_file.open("osm_tram_stops_and_tracks.pickle") as file:
            return pickle.load(file)


@pytest.fixture
def krakow_tram_network_graph() -> nx.DiGraph:
    with zipfile.ZipFile("tests/assets/krakow_tram_network_graph.zip") as zip_file:
        with zip_file.open("krakow_tram_network_graph.pickle") as file:
            return pickle.load(file)


@pytest.fixture
def tram_trips_by_id() -> dict[str, list[int]]:
    with zipfile.ZipFile("tests/assets/tram_trips_by_id.zip") as zip_file:
        with zip_file.open("tram_trips_by_id.json") as file:
            return json.load(file)


@pytest.fixture
def krakow_city_configuration():
    return CityConfiguration.from_path(
        Path.cwd() / "tests" / "assets" / "krakow_city_configuration.json"
    )


@pytest.fixture
def osm_tram_track_crossings() -> overpy.Result:
    with zipfile.ZipFile(
        "tests/assets/tram_track_crossings_overpass_query_result.zip"
    ) as zip_file:
        with zip_file.open("osm_tram_track_crossings.pickle") as file:
            return pickle.load(file)


@pytest.fixture
def osm_tram_stops() -> overpy.Result:
    with zipfile.ZipFile(
        "tests/assets/tram_stops_overpass_query_result.zip"
    ) as zip_file:
        with zip_file.open("osm_tram_stops.pickle") as file:
            return pickle.load(file)
