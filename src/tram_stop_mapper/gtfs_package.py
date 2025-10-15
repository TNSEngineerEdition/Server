from collections import defaultdict
from functools import cached_property
from io import BytesIO
from pathlib import Path
from typing import Any, cast, ClassVar, Generator, IO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict, field_validator

from tram_stop_mapper.exceptions import InvalidGTFSPackage
from tram_stop_mapper.weekday import Weekday


class GTFSPackage(BaseModel):
    FILE_NAMES: ClassVar[list[str]] = [
        "stops.txt",
        "routes.txt",
        "trips.txt",
        "stop_times.txt",
        "calendar.txt",
    ]

    STOPS_COLUMNS: ClassVar[list[str]] = [
        "stop_id",
        "stop_code",
        "stop_name",
        "stop_desc",
        "stop_lat",
        "stop_lon",
        "zone_id",
        "stop_url",
        "location_type",
        "parent_station",
        "stop_timezone",
        "wheelchair_boarding",
        "platform_code",
    ]

    ROUTES_COLUMNS: ClassVar[list[str]] = [
        "route_id",
        "agency_id",
        "route_short_name",
        "route_long_name",
        "route_desc",
        "route_type",
        "route_url",
        "route_color",
        "route_text_color",
    ]

    TRIPS_COLUMNS: ClassVar[list[str]] = [
        "trip_id",
        "route_id",
        "service_id",
        "trip_headsign",
        "trip_short_name",
        "direction_id",
        "block_id",
        "shape_id",
        "wheelchair_accessible",
    ]

    STOP_TIMES_COLUMNS: ClassVar[list[str]] = [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
        "stop_headsign",
        "pickup_type",
        "drop_off_type",
        "shape_dist_traveled",
        "timepoint",
    ]

    CALENDAR_COLUMNS: ClassVar[list[str]] = [
        "service_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "start_date",
        "end_date",
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stops: pd.DataFrame
    routes: pd.DataFrame
    trips: pd.DataFrame
    stop_times: pd.DataFrame
    calendar: pd.DataFrame

    @staticmethod
    def _validate_columns(
        file_name: str,
        data_frame: pd.DataFrame,
        expected_columns: list[str],
    ) -> pd.DataFrame:
        if (columns := list(data_frame.columns)) != expected_columns:
            raise InvalidGTFSPackage(
                f"File {file_name} should contain columns: {expected_columns}, instead got: {columns}"
            )

        return data_frame

    @field_validator("stops", mode="before")
    @classmethod
    def validate_stops_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns("stops.txt", value, cls.STOPS_COLUMNS[1:])

    @field_validator("routes", mode="before")
    @classmethod
    def validate_routes_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns("routes.txt", value, cls.ROUTES_COLUMNS[1:])

    @field_validator("trips", mode="before")
    @classmethod
    def validate_trips_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns("trips.txt", value, cls.TRIPS_COLUMNS[1:])

    @field_validator("stop_times", mode="before")
    @classmethod
    def validate_stop_times_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns("stop_times.txt", value, cls.STOP_TIMES_COLUMNS)

    @field_validator("calendar", mode="before")
    @classmethod
    def validate_calendar_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns("calendar.txt", value, cls.CALENDAR_COLUMNS)

    @classmethod
    def from_zip_file(cls, zip_file: ZipFile) -> "GTFSPackage":
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
    def from_file(cls, file_path: str | Path) -> "GTFSPackage":
        with ZipFile(file_path) as zip_file:
            return cls.from_zip_file(zip_file)

    @classmethod
    def from_url(cls, url: str) -> "GTFSPackage":
        response = requests.get(url, stream=True)
        zip_file = ZipFile(BytesIO(response.content))
        return cls.from_zip_file(zip_file)

    @cached_property
    def _stop_times_as_dict(self) -> dict[str, dict[tuple[str, int], Any]]:
        return cast(
            dict[str, dict[tuple[str, int], Any]],
            self.stop_times.set_index(["trip_id", "stop_sequence"]).to_dict(),
        )

    @cached_property
    def weekdays_by_service_id(self) -> dict[str, set[Weekday]]:
        return {
            str(row["service_id"]): {day for day in list(Weekday) if row[day] == 1}
            for _, row in self.calendar.iterrows()
        }

    @cached_property
    def stop_id_sequence_by_trip_id(self) -> dict[str, list[str]]:
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
    def trip_stop_times_by_trip_id(self) -> dict[str, list[int]]:
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

    def to_zip_file(self, file: IO[bytes]) -> None:
        with ZipFile(file, "w", compression=ZIP_DEFLATED) as zip_file:
            with zip_file.open("stops.txt", "w") as file:
                self.stops.to_csv(file)

            with zip_file.open("routes.txt", "w") as file:
                self.routes.to_csv(file)

            with zip_file.open("trips.txt", "w") as file:
                self.trips.to_csv(file)

            with zip_file.open("stop_times.txt", "w") as file:
                self.stop_times.to_csv(file, index=False)

            with zip_file.open("calendar.txt", "w") as file:
                self.calendar.to_csv(file, index=False)
