from collections import defaultdict
from functools import cached_property
from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict


class GTFSPackage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stops: pd.DataFrame
    routes: pd.DataFrame
    trips: pd.DataFrame
    stop_times: pd.DataFrame

    @classmethod
    def _from_zip_file(cls, zip_file: ZipFile):
        with zip_file.open("stops.txt") as file:
            stops = pd.read_csv(file).set_index("stop_id")

        with zip_file.open("routes.txt") as file:
            routes = pd.read_csv(file).set_index("route_id")

        with zip_file.open("trips.txt") as file:
            trips = pd.read_csv(file).set_index("trip_id")

        with zip_file.open("stop_times.txt") as file:
            stop_times = pd.read_csv(file)

        return cls(stops=stops, routes=routes, trips=trips, stop_times=stop_times)

    @classmethod
    def from_file(cls, file_path: str):
        with ZipFile(file_path) as zip_file:
            return cls._from_zip_file(zip_file)

    @classmethod
    def from_url(cls, url: str):
        response = requests.get(url, stream=True)
        zip_file = ZipFile(BytesIO(response.content))
        return cls._from_zip_file(zip_file)

    @cached_property
    def stop_id_sequence_by_trip_id(self):
        stop_times_dict = self.stop_times.set_index(
            ["trip_id", "stop_sequence"]
        ).to_dict()

        stop_times_dict_for_stop_ids: dict[tuple[str, int], str] = stop_times_dict[
            "stop_id"
        ]
        stop_ids_by_trip_id: defaultdict[str, list[str]] = defaultdict(list)

        for trip_id, stop_sequence in sorted(stop_times_dict_for_stop_ids.keys()):
            stop_ids_by_trip_id[trip_id].append(
                stop_times_dict_for_stop_ids[trip_id, stop_sequence]
            )

        return dict(stop_ids_by_trip_id)
