import pickle
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from constants import FROZEN_DATA_DIRECTORY

from city_data_builder import CityConfiguration
from overpass_client import OverpassClient
from tram_stop_mapper import GTFSPackage


def main(city_configuration_path: Path) -> None:
    current_date_iso = datetime.now().isoformat(timespec="seconds").replace(":", "-")

    city_configuration = CityConfiguration.from_path(city_configuration_path)
    gtfs_package = GTFSPackage.from_url(city_configuration.gtfs_url)

    custom_node_ids: list[int] = []
    for item in city_configuration.custom_stop_mapping.values():
        if isinstance(item, int):
            custom_node_ids.append(item)
        else:
            custom_node_ids.extend(filter(lambda x: x is not None, item))  # type: ignore[arg-type]

    relations_and_stops_query_result = OverpassClient.get_relations_and_stops(
        city_configuration.osm_area_name,
        custom_node_ids,
    )

    tram_stops_and_tracks_query_result = OverpassClient.get_tram_stops_and_tracks(
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


if __name__ == "__main__":
    """
    Example usage: python3 tests/_utils/add_frozen_data_test_case.py config/cities/krakow.json
    """

    main(Path.cwd() / sys.argv[1])
