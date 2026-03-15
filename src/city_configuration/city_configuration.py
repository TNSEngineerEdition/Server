import logging
import os
from functools import cached_property
from pathlib import Path
from typing import ClassVar, Self

from pydantic import BaseModel, ValidationError

from city_configuration.models import (
    GTFSConfiguration,
    TramStopPairCheck,
)

logger = logging.getLogger(__name__)


class CityConfiguration(BaseModel):
    CITIES_DIRECTORY_PATH: ClassVar[Path] = Path(
        os.environ.get("CITIES_DIRECTORY_PATH", "./cities")
    )

    city: str
    country: str
    image: str
    osm_area_name: str
    gtfs_configurations: list[GTFSConfiguration]
    ignored_osm_relations: list[int]
    max_distance_ratio: float
    custom_tram_stop_pair_max_distance_checks: list[TramStopPairCheck]

    @classmethod
    def from_path(cls, path: Path) -> Self:
        try:
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            logger.exception(f"Invalid configuration file: {path}", exc_info=exc)
            raise

    @classmethod
    def _get_latest_in_directory(cls, city_directory: Path) -> Self:
        latest_configuration_path = max(
            config_file
            for config_file in city_directory.iterdir()
            if config_file.is_file() and str(config_file).endswith(".json")
        )

        return cls.from_path(latest_configuration_path)

    @classmethod
    def get_all(cls) -> dict[str, Self]:
        return {
            city_directory.name: cls._get_latest_in_directory(city_directory)
            for city_directory in cls.CITIES_DIRECTORY_PATH.iterdir()
            if city_directory.is_dir() and any(city_directory.iterdir())
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
