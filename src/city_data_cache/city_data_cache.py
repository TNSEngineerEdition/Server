import datetime
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from filelock import FileLock

from city_data_builder import ResponseCityData


class CityDataCache:
    DEFAULT_CACHE_DIRECTORY = Path(
        os.environ.get("CITY_DATA_CACHE_DIRECTORY", "./cache/cities")
    )
    DEFAULT_MAX_FILE_COUNT = int(os.environ.get("CITY_DATA_CACHE_MAX_FILE_COUNT", "10"))

    def __init__(
        self,
        cache_directory: Path = DEFAULT_CACHE_DIRECTORY,
        max_file_count: int = DEFAULT_MAX_FILE_COUNT,
    ) -> None:
        self.cache_directory = cache_directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.max_file_count = max_file_count

    def _zip_city_path(self, city_id: str) -> Path:
        return self.cache_directory / f"{city_id}.zip"

    def lock(self, city_id: str) -> FileLock:
        return FileLock(self._zip_city_path(city_id).with_suffix(".lock"))

    def get(self, city_id: str, date: datetime.date) -> ResponseCityData | None:
        city_zip_path = self._zip_city_path(city_id)
        file_name = date.isoformat()

        if not city_zip_path.exists():
            return None

        with ZipFile(city_zip_path) as zip_file:
            if file_name not in zip_file.namelist():
                return None
            with zip_file.open(file_name) as file:
                return ResponseCityData.model_validate_json(file.read())

    def get_cached_dates(self, city_id: str) -> list[datetime.date]:
        city_zip_path = self._zip_city_path(city_id)
        if not city_zip_path.exists():
            return []

        with ZipFile(city_zip_path) as zip_file:
            return sorted(
                [datetime.date.fromisoformat(name) for name in zip_file.namelist()],
                reverse=True,
            )

    def _rebuild_zip(self, zip_file: ZipFile, files_to_copy: list[str]) -> Path:
        with tempfile.NamedTemporaryFile("wb", delete=False) as temp_file:
            tmp_path = Path(temp_file.name)

        with ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as zip_write:
            for item in files_to_copy:
                with zip_file.open(item) as file_to_copy:
                    zip_write.writestr(item, file_to_copy.read())

        return tmp_path

    def _remove_redundant_files(self, city_zip_path: Path) -> None:
        with ZipFile(city_zip_path) as zip_file:
            files = [name for name in zip_file.namelist()]
            if len(files) < self.max_file_count:
                return
            files.sort(reverse=True)
            files_to_copy = files[: self.max_file_count - 1]
            tmp_path = self._rebuild_zip(zip_file, files_to_copy)

        shutil.move(str(tmp_path), str(city_zip_path))

    def store(
        self,
        city_id: str,
        date: datetime.date,
        city_data: ResponseCityData,
    ) -> ResponseCityData:
        city_zip_path = self._zip_city_path(city_id)
        file_name = date.isoformat()

        if city_zip_path.exists():
            self._remove_redundant_files(city_zip_path)

        with ZipFile(city_zip_path, "a", compression=ZIP_DEFLATED) as zip_file:
            zip_file.writestr(file_name, city_data.model_dump_json())

        return city_data
