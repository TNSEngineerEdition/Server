import io
from collections import defaultdict
from pathlib import Path
from typing import Any, Generator, IO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pandas as pd
import pytest

from tram_stop_mapper.gtfs_package import GTFSPackage


class TestGTFSPackage:
    GTFS_FILE_PATH = Path.cwd() / "tests" / "assets" / "gtfs_schedule.zip"

    @pytest.fixture
    def gtfs_package_byte_buffer_missing_columns(
        self, gtfs_package: GTFSPackage, invalid_file_name: str
    ) -> Generator[IO[bytes], None, None]:
        match invalid_file_name:
            case "stops.txt":
                gtfs_package.stops.drop(
                    columns=[GTFSPackage.STOPS_COLUMNS[-1]], inplace=True
                )
            case "routes.txt":
                gtfs_package.routes.drop(
                    columns=[GTFSPackage.ROUTES_COLUMNS[-1]], inplace=True
                )
            case "trips.txt":
                gtfs_package.trips.drop(
                    columns=[GTFSPackage.TRIPS_COLUMNS[-1]], inplace=True
                )
            case "stop_times.txt":
                gtfs_package.stop_times.drop(
                    columns=[GTFSPackage.STOP_TIMES_COLUMNS[-1]], inplace=True
                )
            case "calendar.txt":
                gtfs_package.calendar.drop(
                    columns=[GTFSPackage.CALENDAR_COLUMNS[-1]], inplace=True
                )
            case _:  # pragma: no cover
                pytest.fail(f"Unknown file name: {invalid_file_name}")

        with io.BytesIO() as file:
            gtfs_package.to_zip_file(file)
            yield file

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

    def test_from_zip_file(self) -> None:
        # Arrange
        with ZipFile(self.GTFS_FILE_PATH) as zip_file:
            # Act
            gtfs_package = GTFSPackage.from_zip_file(zip_file)

        # Assert
        self._assert_data_frame_content(
            data_frame=gtfs_package.stops,
            columns=GTFSPackage.STOPS_COLUMNS[1:],
            row_count=353,
            index_name=GTFSPackage.STOPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.routes,
            columns=GTFSPackage.ROUTES_COLUMNS[1:],
            row_count=26,
            index_name=GTFSPackage.ROUTES_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.trips,
            columns=GTFSPackage.TRIPS_COLUMNS[1:],
            row_count=18478,
            index_name=GTFSPackage.TRIPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.stop_times,
            columns=GTFSPackage.STOP_TIMES_COLUMNS,
            row_count=481672,
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.calendar,
            columns=GTFSPackage.CALENDAR_COLUMNS,
            row_count=5,
        )

    @pytest.mark.parametrize("excluded_file_name", GTFSPackage.FILE_NAMES)
    def test_from_zip_file_missing_files(
        self,
        gtfs_package_byte_buffer_selected_files: io.BytesIO,
        excluded_file_name: str,
    ) -> None:
        # Act
        with (
            ZipFile(gtfs_package_byte_buffer_selected_files) as zip_file,
            pytest.raises(
                KeyError,
                match=f"There is no item named '{excluded_file_name}' in the archive",
            ),
        ):
            GTFSPackage.from_zip_file(zip_file)

    @pytest.mark.parametrize("invalid_file_name", GTFSPackage.FILE_NAMES)
    def test_from_zip_file_missing_columns(
        self,
        gtfs_package_byte_buffer_missing_columns: io.BytesIO,
        invalid_file_name: str,
    ) -> None:
        # Act
        with (
            ZipFile(gtfs_package_byte_buffer_missing_columns) as zip_file,
            pytest.raises(
                ValueError,
                match=f"Invalid GTFS data: File {invalid_file_name} should contain columns",
            ),
        ):
            GTFSPackage.from_zip_file(zip_file)

    def test_from_file(self) -> None:
        # Act
        gtfs_package = GTFSPackage.from_file(self.GTFS_FILE_PATH)

        # Assert
        self._assert_data_frame_content(
            data_frame=gtfs_package.stops,
            columns=GTFSPackage.STOPS_COLUMNS[1:],
            row_count=353,
            index_name=GTFSPackage.STOPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.routes,
            columns=GTFSPackage.ROUTES_COLUMNS[1:],
            row_count=26,
            index_name=GTFSPackage.ROUTES_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.trips,
            columns=GTFSPackage.TRIPS_COLUMNS[1:],
            row_count=18478,
            index_name=GTFSPackage.TRIPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.stop_times,
            columns=GTFSPackage.STOP_TIMES_COLUMNS,
            row_count=481672,
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.calendar,
            columns=GTFSPackage.CALENDAR_COLUMNS,
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
            columns=GTFSPackage.STOPS_COLUMNS[1:],
            row_count=353,
            index_name=GTFSPackage.STOPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.routes,
            columns=GTFSPackage.ROUTES_COLUMNS[1:],
            row_count=26,
            index_name=GTFSPackage.ROUTES_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.trips,
            columns=GTFSPackage.TRIPS_COLUMNS[1:],
            row_count=18478,
            index_name=GTFSPackage.TRIPS_COLUMNS[0],
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.stop_times,
            columns=GTFSPackage.STOP_TIMES_COLUMNS,
            row_count=481672,
        )

        self._assert_data_frame_content(
            data_frame=gtfs_package.calendar,
            columns=GTFSPackage.CALENDAR_COLUMNS,
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

    @pytest.mark.parametrize(
        ("ignored_route_names", "route_count"),
        [(set(), 26), ({"13"}, 25), ({"1", "194"}, 25)],
    )
    def test_get_route_names_and_ids(
        self, ignored_route_names: set[str], route_count: int
    ) -> None:
        # Arrange
        gtfs_package = GTFSPackage.from_file(self.GTFS_FILE_PATH)

        # Act
        route_names_and_ids = gtfs_package.get_route_names_and_ids(
            ignored_route_names=ignored_route_names
        )

        # Assert
        assert isinstance(route_names_and_ids, Generator)

        routes = list(route_names_and_ids)
        assert len(routes) == route_count

        for route_name, route_id in routes:
            assert route_name not in ignored_route_names

            route_row = gtfs_package.routes.loc[route_id]
            assert str(route_row["route_short_name"]) == route_name
