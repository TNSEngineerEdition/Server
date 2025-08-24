from collections import defaultdict
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from tram_stop_mapper import GTFSPackage


class TestGTFSPackage:
    GTFS_STOPS_COLUMNS = [
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

    GTFS_ROUTES_COLUMNS = [
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

    GTFS_TRIPS_COLUMNS = [
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

    GTFS_STOP_TIMES_COLUMNS = [
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

    GTFS_CALENDAR_COLUMNS = [
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

    GTFS_FILE_PATH = Path.cwd() / "tests" / "assets" / "gtfs_schedule.zip"

    @staticmethod
    def _assert_data_frame_content(
        data_frame: Any,
        columns: list[str],
        row_count: int,
        index_name: str | None = None,
    ) -> None:
        assert isinstance(data_frame, pd.DataFrame)
        assert data_frame.index.name == index_name
        assert list(data_frame.columns) == columns
        assert len(data_frame) == row_count

    def test_from_file(self) -> None:
        # Act
        gtfs_package = GTFSPackage.from_file(self.GTFS_FILE_PATH)

        # Assert
        self._assert_data_frame_content(
            data_frame=gtfs_package.stops,
            columns=self.GTFS_STOPS_COLUMNS[1:],
            row_count=353,
            index_name=self.GTFS_STOPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.routes,
            columns=self.GTFS_ROUTES_COLUMNS[1:],
            row_count=26,
            index_name=self.GTFS_ROUTES_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.trips,
            columns=self.GTFS_TRIPS_COLUMNS[1:],
            row_count=18478,
            index_name=self.GTFS_TRIPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.stop_times,
            columns=self.GTFS_STOP_TIMES_COLUMNS,
            row_count=481672,
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.calendar,
            columns=self.GTFS_CALENDAR_COLUMNS,
            row_count=5,
        )

    @patch("requests.get")
    def test_from_url(self, get_mock: MagicMock) -> None:
        # Arrange
        url = "http://example.com/gtfs.zip"

        get_mock.return_value = MagicMock(content=self.GTFS_FILE_PATH.read_bytes())

        # Act
        gtfs_package = GTFSPackage.from_url(url)

        # Assert
        get_mock.assert_called_once_with(url, stream=True)

        self._assert_data_frame_content(
            data_frame=gtfs_package.stops,
            columns=self.GTFS_STOPS_COLUMNS[1:],
            row_count=353,
            index_name=self.GTFS_STOPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.routes,
            columns=self.GTFS_ROUTES_COLUMNS[1:],
            row_count=26,
            index_name=self.GTFS_ROUTES_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.trips,
            columns=self.GTFS_TRIPS_COLUMNS[1:],
            row_count=18478,
            index_name=self.GTFS_TRIPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.stop_times,
            columns=self.GTFS_STOP_TIMES_COLUMNS,
            row_count=481672,
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.calendar,
            columns=self.GTFS_CALENDAR_COLUMNS,
            row_count=5,
        )

    def test_stop_id_sequence_by_trip_id(self) -> None:
        # Arrange
        gtfs_package = GTFSPackage.from_file(self.GTFS_FILE_PATH)

        sorted_stop_times = gtfs_package.stop_times.sort_values(
            ["trip_id", "stop_sequence"]
        )

        index_by_trip_id: defaultdict[str, int] = defaultdict(int)

        # Act
        stop_id_sequence_by_trip_id = gtfs_package.stop_id_sequence_by_trip_id

        # Assert
        assert set(stop_id_sequence_by_trip_id.keys()) == set(gtfs_package.trips.index)

        for _, row in sorted_stop_times.iterrows():
            trip_id = row["trip_id"]
            assert (
                stop_id_sequence_by_trip_id[trip_id][index_by_trip_id[trip_id]]
                == row["stop_id"]
            )

            index_by_trip_id[trip_id] += 1

        # Make sure the property isn't re-calculated every time for better performance
        assert stop_id_sequence_by_trip_id is gtfs_package.stop_id_sequence_by_trip_id

    def test_trip_stop_times_by_trip_id(self) -> None:
        # Arrange
        gtfs_package = GTFSPackage.from_file(self.GTFS_FILE_PATH)

        # Act
        trip_stop_times_by_trip_id = gtfs_package.trip_stop_times_by_trip_id

        # Assert
        assert set(trip_stop_times_by_trip_id.keys()) == set(gtfs_package.trips.index)

        assert all(
            trip_stops[i] <= trip_stops[i + 1]
            for trip_stops in trip_stop_times_by_trip_id.values()
            for i in range(len(trip_stops) - 1)
        )
