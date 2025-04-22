import pickle
import sys
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile

from src.model import CityConfiguration, GTFSPackage
from src.overpass_client import OverpassClient
from tests.constants import FROZEN_DATA_DIRECTORY
from util_overpass_client import UtilOverpassClient


def main(city_configuration_path: str):
    util_overpass_client = UtilOverpassClient()

    with open(city_configuration_path) as file:
        city_configuration = CityConfiguration.model_validate_json(file.read())

    current_date_iso = datetime.now().isoformat(timespec="seconds").replace(":", "-")

    gtfs_package = GTFSPackage.from_url(city_configuration.gtfs_url)

    relations_and_stops_query_result = OverpassClient.get_relations_and_stops(
        city_configuration.osm_area_name,
        city_configuration.custom_stop_mapping.values(),
    )

    tram_stops_and_tracks_query_result = OverpassClient.get_tram_stops_and_tracks(
        city_configuration.osm_area_name
    )

    osm_tram_stops = util_overpass_client.get_tram_stops(
        city_configuration.osm_area_name
    )

    osm_tram_track_crossings = util_overpass_client.get_tram_track_crossings(
        city_configuration.osm_area_name
    )

    with ZipFile(
        FROZEN_DATA_DIRECTORY / (current_date_iso + ".zip"), "w", ZIP_DEFLATED
    ) as zip_file:
        with zip_file.open("city_configuration.json", "w") as file:
            file.write(city_configuration.model_dump_json().encode())

        with zip_file.open("gtfs_package.pickle", "w") as file:
            pickle.dump(gtfs_package, file)

        with zip_file.open("relations_and_stops_query_result.pickle", "w") as file:
            pickle.dump(relations_and_stops_query_result, file)

        with zip_file.open("tram_stops_and_tracks_query_result.pickle", "w") as file:
            pickle.dump(tram_stops_and_tracks_query_result, file)

        with zip_file.open("osm_tram_stops.pickle", "w") as file:
            pickle.dump(osm_tram_stops, file)

        with zip_file.open("osm_tram_track_crossings.pickle", "w") as file:
            pickle.dump(osm_tram_track_crossings, file)


if __name__ == "__main__":
    """
    Example usage: python3 tests/_utils/add_frozen_data_test_case.py config/cities/krakow.json
    """

    main(sys.argv[1])
