from collections import defaultdict
from functools import cached_property
from io import BytesIO
from typing import Any
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
    calendar: pd.DataFrame

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

        with zip_file.open("calendar.txt") as file:
            calendar = pd.read_csv(file)

        return cls(
            stops=stops,
            routes=routes,
            trips=trips,
            stop_times=stop_times,
            calendar=calendar,
        )

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
    def _stop_times_as_dict(self) -> dict[str, dict[tuple[str, int], Any]]:
        return self.stop_times.set_index(["trip_id", "stop_sequence"]).to_dict()

    @cached_property
    def _service_id_as_dict(self) -> dict[str, set[str]]:
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        result: defaultdict[str, list[str]] = defaultdict(list)
        for _, row in self.calendar.iterrows():
            service_id = row["service_id"]
            service_days = [day for day in days if row[day] == 1]
            result[service_id] = set(service_days)
        return dict(result)

    @cached_property
    def stop_id_sequence_by_trip_id(self):
        stop_ids = self._stop_times_as_dict["stop_id"]

        result: defaultdict[str, list[str]] = defaultdict(list)
        for trip_id, stop_sequence in sorted(stop_ids.keys()):
            result[trip_id].append(stop_ids[trip_id, stop_sequence])

        return dict(result)

    @staticmethod
    def _time_string_to_seconds(time_str: str) -> int:
        hour, minute, second = map(int, time_str.split(":"))
        return (hour * 60 + minute) * 60 + second

    @cached_property
    def trip_data_and_stops_by_trip_id(self):
        stop_ids = self._stop_times_as_dict["stop_id"]
        departure_times = self._stop_times_as_dict["departure_time"]
        service_id_to_days = self._service_id_as_dict
        trip_stops_by_trip_id: defaultdict[str, list[tuple[str, int]]] = defaultdict(
            list
        )
        for trip_id, stop_sequence in sorted(stop_ids.keys()):
            trip_stops_by_trip_id[trip_id].append(
                (
                    stop_ids[trip_id, stop_sequence],
                    self._time_string_to_seconds(
                        departure_times[trip_id, stop_sequence]
                    ),
                )
            )

        trip_data_by_trip_id: defaultdict[str, dict[str, Any]] = defaultdict(dict)
        for trip_id, trip_row in self.trips.iterrows():
            service_id = trip_row["service_id"]
            for name, value in trip_row.items():
                if name == "service_id":
                    trip_data_by_trip_id[trip_id]["service_days"] = list(
                        service_id_to_days.get(service_id)
                    )
                else:
                    trip_data_by_trip_id[trip_id][name] = value
            for name, value in self.routes.loc[trip_row["route_id"]].items():
                trip_data_by_trip_id[trip_id][name] = value

        return dict(trip_data_by_trip_id), dict(trip_stops_by_trip_id)
