import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, IO
from unittest.mock import MagicMock, patch

import pytest
import requests
from freezegun import freeze_time

from city_configuration import GTFSConfiguration
from gtfs.exceptions import MissingGTFSPackage
from gtfs.gtfs_package import GTFSPackage
from gtfs.gtfs_package_store import GTFSPackageStore


class TestGTFSPackageStore:
    EXAMPLE_CONFIG = GTFSConfiguration(file_url="https://gtfs.example.com/GTFS.zip")
    EXAMPLE_CONFIG_FILE_URL_HASH = "2e997655433a4916518a9c1a065bf377"

    @pytest.fixture
    def empty_cache_directory(self) -> Generator[Path, None, None]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def filled_cache_directory(
        self, empty_cache_directory: Path, gtfs_package: GTFSPackage
    ) -> Path:
        with (empty_cache_directory / self.EXAMPLE_CONFIG_FILE_URL_HASH).open(
            "wb"
        ) as file:
            gtfs_package.to_zip_file(file)

        return empty_cache_directory

    def test_load_gtfs_package(
        self, filled_cache_directory: Path, gtfs_package: GTFSPackage
    ) -> None:
        # Arrange
        gtfs_schedule_store = GTFSPackageStore(filled_cache_directory)

        # Act
        gtfs_schedule = gtfs_schedule_store.load_gtfs_package(self.EXAMPLE_CONFIG)

        # Assert
        assert gtfs_schedule == gtfs_package

    @patch("requests.get")
    def test_load_gtfs_package_new_file(
        self,
        mock_get: MagicMock,
        empty_cache_directory: Path,
        gtfs_package: GTFSPackage,
        gtfs_package_byte_buffer: IO[bytes],
    ) -> None:
        # Arrange
        requests_response = requests.Response()
        requests_response.status_code = 200
        requests_response._content = gtfs_package_byte_buffer.read()
        requests_response.request = requests.PreparedRequest()
        requests_response.request.method = "GET"
        requests_response.request.url = self.EXAMPLE_CONFIG.file_url

        mock_get.return_value = requests_response

        gtfs_schedule_store = GTFSPackageStore(empty_cache_directory)

        # Act
        gtfs_schedule = gtfs_schedule_store.load_gtfs_package(self.EXAMPLE_CONFIG)

        # Assert
        assert gtfs_schedule == gtfs_package

        mock_get.assert_called_once_with(
            self.EXAMPLE_CONFIG.file_url, stream=True, timeout=600
        )

    @patch("requests.get")
    def test_load_gtfs_package_new_file_download_error(
        self,
        mock_get: MagicMock,
        empty_cache_directory: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        requests_response = requests.Response()
        requests_response.status_code = 404
        requests_response.request = requests.PreparedRequest()
        requests_response.request.method = "GET"
        requests_response.request.url = self.EXAMPLE_CONFIG.file_url
        mock_get.return_value = requests_response

        gtfs_schedule_store = GTFSPackageStore(empty_cache_directory)

        # Act
        with (
            pytest.raises(MissingGTFSPackage) as exc_info,
            caplog.at_level(logging.ERROR, "gtfs.gtfs_package"),
        ):
            gtfs_schedule_store.load_gtfs_package(
                self.EXAMPLE_CONFIG,
            )

        # Assert
        assert self.EXAMPLE_CONFIG.file_url in str(exc_info.value)
        assert (
            f"Error while downloading GTFS Schedule file from {self.EXAMPLE_CONFIG.file_url}"
            in caplog.text
        )

        mock_get.assert_called_once_with(
            self.EXAMPLE_CONFIG.file_url, stream=True, timeout=600
        )

    @patch("requests.get")
    @patch("gtfs.gtfs_package.GTFSPackage.from_file")
    @freeze_time(datetime.now() + timedelta(days=1, hours=1))
    def test_load_gtfs_package_outdated_file(
        self,
        mock_from_file: MagicMock,
        mock_get: MagicMock,
        filled_cache_directory: Path,
        gtfs_package: GTFSPackage,
        gtfs_package_byte_buffer: IO[bytes],
    ) -> None:
        # Arrange
        requests_response = requests.Response()
        requests_response.status_code = 200
        requests_response._content = gtfs_package_byte_buffer.read()
        requests_response.request = requests.PreparedRequest()
        requests_response.request.method = "GET"
        requests_response.request.url = self.EXAMPLE_CONFIG.file_url
        mock_get.return_value = requests_response

        gtfs_schedule_store = GTFSPackageStore(filled_cache_directory)

        # Act
        gtfs_schedule = gtfs_schedule_store.load_gtfs_package(self.EXAMPLE_CONFIG)

        # Assert
        assert gtfs_schedule == gtfs_package
        mock_get.assert_called_once_with(
            self.EXAMPLE_CONFIG.file_url, stream=True, timeout=600
        )
        mock_from_file.assert_not_called()

    @patch("gtfs.gtfs_package.GTFSPackage.from_file")
    @freeze_time(datetime.now() + timedelta(hours=1))
    def test_load_gtfs_package_from_cache(
        self,
        mock_from_file: MagicMock,
        filled_cache_directory: Path,
        gtfs_package: GTFSPackage,
    ) -> None:
        # Arrange
        mock_from_file.return_value = gtfs_package

        gtfs_schedule_store = GTFSPackageStore(filled_cache_directory)

        # Load for the first time - the second call should be cached
        gtfs_schedule_store.load_gtfs_package(self.EXAMPLE_CONFIG)

        # Act
        gtfs_schedule = gtfs_schedule_store.load_gtfs_package(self.EXAMPLE_CONFIG)

        # Assert
        assert gtfs_schedule == gtfs_package
        mock_from_file.assert_called_once_with(
            filled_cache_directory / self.EXAMPLE_CONFIG_FILE_URL_HASH,
        )
