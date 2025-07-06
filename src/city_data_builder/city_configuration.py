import logging
import os
from functools import cached_property
from pathlib import Path
from typing import ClassVar, Self

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class CustomTramStopPairMapping(BaseModel):
    source_gtfs_stop_id: str
    source_osm_node_id: int
    destination_gtfs_stop_id: str
    destination_osm_node_id: int


class TramStopPairCheck(BaseModel):
    source: int
    destination: int
    ratio: float


class CityConfiguration(BaseModel):
    CITIES_DIRECTORY_PATH: ClassVar[Path] = Path(
        os.environ.get("CITIES_DIRECTORY_PATH", "./cities")
    )

    osm_area_name: str
    gtfs_url: str
    ignored_gtfs_lines: list[str]
    ignored_osm_relations: list[int]
    custom_stop_mapping: dict[str, int | tuple[int | None, int | None, int | None]]
    custom_stop_pair_mapping: list[CustomTramStopPairMapping]
    max_distance_ratio: float
    custom_tram_stop_pair_max_distance_checks: list[TramStopPairCheck]

    @classmethod
    def from_path(cls, path: Path):
        try:
            return cls.model_validate_json(path.read_text())
        except ValidationError as exc:
            logger.exception(f"Invalid configuration file: {path}", exc_info=exc)
            raise

    @classmethod
    def _get_latest_in_directory(cls, city_directory: Path):
        latest_configuration_path = max(
            config_file
            for config_file in city_directory.iterdir()
            if config_file.is_file() and str(config_file).endswith(".json")
        )

        return cls.from_path(latest_configuration_path)

    @classmethod
    def get_all(cls):
        return {
            city_directory.name: cls._get_latest_in_directory(city_directory)
            for city_directory in cls.CITIES_DIRECTORY_PATH.iterdir()
            if city_directory.is_dir()
        }

    @classmethod
    def get_by_city_id(cls, city_id: str) -> Self | None:
        configuration_city = cls.CITIES_DIRECTORY_PATH / city_id
        if not configuration_city.is_dir():
            return None

        return cls._get_latest_in_directory(configuration_city)

    @cached_property
    def custom_tram_stop_pair_ratio_map(self) -> dict[tuple[int, int], float]:
        return {
            (item.source, item.destination): item.ratio
            for item in self.custom_tram_stop_pair_max_distance_checks
        }

    @cached_property
    def custom_stop_pair_by_gtfs_stop_ids(self):
        return {
            (item.source_gtfs_stop_id, item.destination_gtfs_stop_id): (
                item.source_osm_node_id,
                item.destination_osm_node_id,
            )
            for item in self.custom_stop_pair_mapping
        }
