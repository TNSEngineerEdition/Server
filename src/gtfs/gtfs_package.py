import datetime
import re
from collections import defaultdict
from functools import cached_property
from io import BytesIO
from pathlib import Path
from typing import Any, cast, ClassVar, Generator, IO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict, field_validator

from gtfs.exceptions import InvalidGTFSPackage
from gtfs.weekday import Weekday


class GTFSPackage(BaseModel):
    FILE_NAMES: ClassVar[list[str]] = [
        "stops.txt",
        "routes.txt",
        "trips.txt",
        "stop_times.txt",
        "calendar.txt",
    ]

    STOPS_COLUMNS: ClassVar[list[str]] = ["stop_id", "stop_name"]

    ROUTES_COLUMNS: ClassVar[list[str]] = [
        "route_id",
        "route_short_name",
        "route_color",
        "route_text_color",
    ]

    TRIPS_COLUMNS: ClassVar[list[str]] = [
        "trip_id",
        "route_id",
        "service_id",
        "trip_headsign",
    ]

    STOP_TIMES_COLUMNS: ClassVar[list[str]] = [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
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

    CALENDAR_DATES_COLUMNS: ClassVar[list[str]] = [
        "service_id",
        "date",
        "exception_type",
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stops: pd.DataFrame
    routes: pd.DataFrame
    trips: pd.DataFrame
    stop_times: pd.DataFrame
    calendar: pd.DataFrame
    calendar_dates: pd.DataFrame

    @staticmethod
    def _validate_columns(
        file_name: str,
        data_frame: pd.DataFrame,
        expected_columns: list[str],
    ) -> pd.DataFrame:
        if not (columns := set(data_frame.columns)).issuperset(expected_columns):
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

    @field_validator("calendar_dates", mode="before")
    @classmethod
    def validate_calendar_dates_columns(cls, value: pd.DataFrame) -> pd.DataFrame:
        return cls._validate_columns(
            "calendar_dates.txt", value, cls.CALENDAR_DATES_COLUMNS
        )

    @classmethod
    def from_zip_file(cls, zip_file: ZipFile) -> "GTFSPackage":
        with zip_file.open("stops.txt") as file:
            stops = pd.read_csv(file)
            stops["stop_id"] = stops["stop_id"].astype(str)
            stops = stops.set_index("stop_id")

        with zip_file.open("routes.txt") as file:
            routes = pd.read_csv(file)
            routes["route_id"] = routes["route_id"].astype(str)
            routes = routes.set_index("route_id")

        with zip_file.open("trips.txt") as file:
            trips = pd.read_csv(file, low_memory=False)
            trips["trip_id"] = trips["trip_id"].astype(str)
            trips = trips.set_index("trip_id")

        with zip_file.open("stop_times.txt") as file:
            stop_times = pd.read_csv(file)

        with zip_file.open("calendar.txt") as file:
            calendar = pd.read_csv(file)

        with zip_file.open("calendar_dates.txt") as file:
            calendar_dates = pd.read_csv(file)

        return cls(
            stops=stops,
            routes=routes,
            trips=trips,
            stop_times=stop_times,
            calendar=calendar,
            calendar_dates=calendar_dates,
        )

    @classmethod
    def from_file(cls, file_path: str | Path) -> "GTFSPackage":
        with ZipFile(file_path) as zip_file:
            return cls.from_zip_file(zip_file)

    @classmethod
    def from_url(cls, url: str) -> "GTFSPackage":
        response = requests.get(url, stream=True, timeout=600)
        response.raise_for_status()

        with ZipFile(BytesIO(response.content)) as zip_file:
            return cls.from_zip_file(zip_file)

    @staticmethod
    def _compare_attribute(attr_name: str, self_attr: Any, other_attr: Any) -> None:
        match self_attr:
            case pd.DataFrame():
                assert self_attr.equals(other_attr)
            case list():
                assert self_attr == other_attr
            case None:
                assert other_attr is None
            case _:  # pragma: no cover
                raise TypeError(
                    f"Unknown attribute {attr_name} type: {type(self_attr)}"
                )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return False

        for attr_name in self.__annotations__:
            self_attr = getattr(self, attr_name)
            other_attr = getattr(other, attr_name)

            try:
                self._compare_attribute(attr_name, self_attr, other_attr)
            except AssertionError:
                return False

        return True

    def replace_file(self, target_file_path: Path) -> None:
        new_file_path = target_file_path.with_suffix(".new")

        try:
            with new_file_path.open("wb") as file:
                self.to_zip_file(file)

            new_file_path.replace(target_file_path)
        finally:
            new_file_path.unlink(missing_ok=True)

    @cached_property
    def _stop_times_as_dict(self) -> dict[str, dict[tuple[str, int], Any]]:
        return cast(
            dict[str, dict[tuple[str, int], Any]],
            self.stop_times.set_index(["trip_id", "stop_sequence"]).to_dict(),
        )

    @cached_property
    def service_ids_by_weekday(self) -> dict[Weekday, set[str]]:
        return {
            weekday: {
                str(row["service_id"])
                for _, row in self.calendar.iterrows()
                if row[weekday] == 1
            }
            for weekday in Weekday
        }

    @cached_property
    def stop_id_sequence_by_trip_id(self) -> dict[str, list[str]]:
        stop_ids = self._stop_times_as_dict["stop_id"]

        result: defaultdict[str, list[str]] = defaultdict(list)
        for trip_id, stop_sequence in sorted(stop_ids.keys()):
            result[trip_id].append(str(stop_ids[trip_id, stop_sequence]))

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

    def get_trips_for_service_ids(
        self, service_ids: set[str]
    ) -> Generator[tuple[str, pd.Series], None, None]:
        return (
            (str(trip_id), trip_data)
            for trip_id, trip_data in self.trips.iterrows()
            if trip_data["service_id"] in service_ids
        )

    def get_route_names_and_ids(
        self, *, ignored_route_names: set[str]
    ) -> Generator[tuple[str, str], None, None]:
        for gtfs_route_id, gtfs_route_row in self.routes.iterrows():
            route_name = str(gtfs_route_row["route_short_name"])
            if route_name in ignored_route_names:
                continue

            yield route_name, str(gtfs_route_id)

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

            with zip_file.open("calendar_dates.txt", "w") as file:
                self.calendar_dates.to_csv(file, index=False)

    def get_service_ids_for_date(self, date: datetime.date) -> set[str]:
        service_ids = self.service_ids_by_weekday[Weekday.from_date(date)]

        exceptions_for_date = self.calendar_dates[
            self.calendar_dates["date"] == int(date.strftime("%Y%m%d"))
        ]

        service_ids_to_add = exceptions_for_date[
            exceptions_for_date["exception_type"] == 1
        ]["service_id"]
        service_ids_to_remove = exceptions_for_date[
            exceptions_for_date["exception_type"] == 2
        ]["service_id"]

        service_ids = service_ids.union(map(str, service_ids_to_add))
        service_ids = service_ids.difference(map(str, service_ids_to_remove))

        return service_ids

    def get_stop_group_name_by_stop_ids(
        self, group_name_pattern: re.Pattern[str], stop_ids: list[str]
    ) -> str | None:
        group_names = [
            group_name_pattern.match(str(self.stops.loc[stop_id]["stop_name"]))
            for stop_id in stop_ids
        ]

        names: set[str] = set()
        for item in group_names:
            if item is None:
                return None

            names.add(str(item.group(1)))

        match len(names):
            case 0:
                return None
            case 1:
                return next(iter(names))
            case _:
                return None
            # Commented-out because some bus stops have been mapped
            # to a single bus stop in city configuration, fixing this
            # requires adding all bus routes to OSM - no time for that
            # case _:  # pragma: no cover
            #     raise ValueError(
            #         f"Duplicate group names {names} found for stop IDs {stop_ids}"
            #     )
