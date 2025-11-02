import io
import json
import pickle
import zipfile
from pathlib import Path
from typing import cast, Generator, IO

import networkx as nx
import overpy
import pytest

from city_data_builder import CityConfiguration, ResponseCityData
from tram_stop_mapper import GTFSPackage
from tram_track_graph_transformer import Node


@pytest.fixture
def gtfs_package() -> GTFSPackage:
    return GTFSPackage.from_file("tests/assets/gtfs_schedule.zip")


@pytest.fixture
def custom_gtfs_package() -> GTFSPackage:
    gtfs_package = GTFSPackage.from_file("tests/assets/gtfs_schedule.zip")

    gtfs_package.routes = gtfs_package.routes[
        gtfs_package.routes["route_short_name"] != 52
    ]

    removed_trips = gtfs_package.trips[gtfs_package.trips["route_id"] == "route_70"]
    gtfs_package.trips = gtfs_package.trips[
        gtfs_package.trips["route_id"] != "route_70"
    ]

    gtfs_package.stop_times = gtfs_package.stop_times[
        ~gtfs_package.stop_times["trip_id"].isin(removed_trips.index)
    ]

    return gtfs_package


@pytest.fixture
def custom_gtfs_package_byte_buffer(
    custom_gtfs_package: GTFSPackage,
) -> Generator[IO[bytes], None, None]:
    with io.BytesIO() as buffer:
        custom_gtfs_package.to_zip_file(buffer)
        buffer.seek(0)
        yield buffer


@pytest.fixture
def gtfs_package_byte_buffer_selected_files(
    gtfs_package: GTFSPackage, excluded_file_name: str
) -> Generator[IO[bytes], None, None]:
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer, "w") as zip_file:
            if excluded_file_name != "stops.txt":
                with zip_file.open("stops.txt", "w") as file:
                    gtfs_package.stops.to_csv(file)

            if excluded_file_name != "routes.txt":
                with zip_file.open("routes.txt", "w") as file:
                    gtfs_package.routes.to_csv(file)

            if excluded_file_name != "trips.txt":
                with zip_file.open("trips.txt", "w") as file:
                    gtfs_package.trips.to_csv(file)

            if excluded_file_name != "stop_times.txt":
                with zip_file.open("stop_times.txt", "w") as file:
                    gtfs_package.stop_times.to_csv(file, index=False)

            if excluded_file_name != "calendar.txt":
                with zip_file.open("calendar.txt", "w") as file:
                    gtfs_package.calendar.to_csv(file, index=False)

        yield buffer


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
def krakow_tram_network_graph() -> "nx.DiGraph[Node]":
    with zipfile.ZipFile("tests/assets/krakow_tram_network_graph.zip") as zip_file:
        with zip_file.open("krakow_tram_network_graph.pickle") as file:
            return cast("nx.DiGraph[Node]", pickle.load(file))


@pytest.fixture
def tram_trips_by_id() -> dict[str, list[int]]:
    with zipfile.ZipFile("tests/assets/tram_trips_by_id.zip") as zip_file:
        with zip_file.open("tram_trips_by_id.json") as file:
            return cast(dict[str, list[int]], json.load(file))


@pytest.fixture
def krakow_city_configuration() -> CityConfiguration:
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


@pytest.fixture
def krakow_response_city_data() -> ResponseCityData:
    with zipfile.ZipFile("tests/assets/krakow_response_city_data.zip") as zip_file:
        with zip_file.open("krakow_response_city_data.json") as file:
            return ResponseCityData.model_validate_json(file.read())
