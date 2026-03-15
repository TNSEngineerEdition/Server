import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

from city_configuration import GTFSConfiguration
from gtfs.exceptions import MissingGTFSPackage
from gtfs.gtfs_package import GTFSPackage

logger = logging.getLogger(__name__)


class GTFSPackageStore:
    DEFAULT_CACHE_DIRECTORY = (
        Path(os.environ.get("CACHE_DIRECTORY", "./cache")) / "gtfs"
    )

    def __init__(self, cache_directory: Path = DEFAULT_CACHE_DIRECTORY) -> None:
        self._cache_directory = cache_directory
        self._cache_directory.mkdir(exist_ok=True)

        self._cached_gtfs_schedules: dict[Path, GTFSPackage] = {}

    @staticmethod
    def _is_cache_outdated(time: datetime) -> bool:
        return time < datetime.now() - timedelta(days=1)

    def _download_gtfs_package(
        self, config: GTFSConfiguration, file_path: Path
    ) -> None:
        try:
            gtfs_schedule = GTFSPackage.from_url(config.file_url)
        except requests.HTTPError as exc:
            logger.exception(
                "Error while downloading GTFS Schedule file from %s",
                config.file_url,
                exc_info=exc,
            )
            return

        gtfs_schedule.replace_file(file_path)
        self._cached_gtfs_schedules[file_path] = gtfs_schedule

    def _load_gtfs_package_from_file(
        self, config: GTFSConfiguration, file_path: Path
    ) -> None:
        if not file_path.is_file():
            raise MissingGTFSPackage(config)

        gtfs_schedule = GTFSPackage.from_file(file_path)
        self._cached_gtfs_schedules[file_path] = gtfs_schedule

    def load_gtfs_package(self, config: GTFSConfiguration) -> GTFSPackage:
        url_hash = hashlib.md5(config.file_url.encode()).hexdigest()
        file_path = self._cache_directory / url_hash

        modification_time = (
            datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_path.exists()
            else datetime.min
        )

        if self._is_cache_outdated(modification_time):
            self._download_gtfs_package(config, file_path)

        if file_path not in self._cached_gtfs_schedules:
            self._load_gtfs_package_from_file(config, file_path)

        return self._cached_gtfs_schedules[file_path]
