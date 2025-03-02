import pickle
import sys
from datetime import datetime

from src.model import CityConfiguration, GTFSPackage
from src.overpass_client import OverpassClient
from tests.tram_stop_mapping.test_tram_stop_mapper import (
    TRAM_STOP_MAPPING_DIRECTORY,
)


def main(city_configuration_path: str):
    with open(city_configuration_path) as file:
        city_configuration = CityConfiguration.model_validate_json(file.read())

    gtfs_package = GTFSPackage.from_url(city_configuration.gtfs_url)
    osm_relations_and_stops = OverpassClient.get_relations_and_stops(
        city_configuration.osm_area_name,
        city_configuration.custom_stop_mapping.values(),
    )

    current_date_iso = datetime.now().isoformat(timespec="seconds")
    target_directory = TRAM_STOP_MAPPING_DIRECTORY / current_date_iso
    target_directory.mkdir()

    with open(target_directory / "city_configuration.pickle", "wb") as file:
        pickle.dump(city_configuration, file)

    with open(target_directory / "gtfs_package.pickle", "wb") as file:
        pickle.dump(gtfs_package, file)

    with open(target_directory / "osm_relations_and_stops.pickle", "wb") as file:
        pickle.dump(osm_relations_and_stops, file)


if __name__ == "__main__":
    """
    Example usage: python3 tests/_utils/add_tram_stop_mapping_test_case.py src/cities/krakow.json
    """

    main(sys.argv[1])
