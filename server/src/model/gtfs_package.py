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
