from collections import defaultdict
from functools import cached_property
from io import BytesIO
from typing import Any, Generator
from zipfile import ZipFile

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict

from src.tram_stop_mapper.weekday import Weekday


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
    def weekdays_by_service_id(self):
        return {
            str(row["service_id"]): {day for day in list(Weekday) if row[day] == 1}
            for _, row in self.calendar.iterrows()
        }

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
    def trip_stop_times_by_trip_id(self):
        stop_ids = self._stop_times_as_dict["stop_id"]
        departure_times = self._stop_times_as_dict["departure_time"]

        result: defaultdict[str, list[int]] = defaultdict(list)
        for trip_id, stop_sequence in sorted(stop_ids.keys()):
            result[trip_id].append(
                self._time_string_to_seconds(departure_times[trip_id, stop_sequence])
            )

        return dict(result)

    def get_trips_for_weekday(
        self, weekday: Weekday
    ) -> Generator[tuple[str, pd.Series], None, None]:
        return (
            (str(trip_id), trip_data)
            for trip_id, trip_data in self.trips.iterrows()
            if weekday in self.weekdays_by_service_id[trip_data["service_id"]]
        )
