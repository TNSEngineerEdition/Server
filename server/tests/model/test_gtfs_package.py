from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
from src.model import GTFSPackage


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

    GTFS_FILE_PATH = "tests/assets/gtfs_schedule.zip"

    @staticmethod
    def _assert_data_frame_content(
        data_frame: Any,
        columns: list[str],
        row_count: int,
        index_name: str | None = None,
    ):
        assert isinstance(data_frame, pd.DataFrame)
        assert data_frame.index.name == index_name
        assert list(data_frame.columns) == columns
        assert len(data_frame) == row_count

    def test_from_file(self):
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

    @patch("requests.get")
    def test_from_url(self, get_mock: MagicMock):
        # Arrange
        url = "http://example.com/gtfs.zip"

        get_mock.return_value = MagicMock()
        with open(self.GTFS_FILE_PATH, "rb") as file:
            get_mock.return_value.content = file.read()

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
