import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from src.city_data_builder import CityConfiguration, CityDataBuilder
from src.city_data_cache import CityDataCache, ResponseCityData
from src.tram_stop_mapper.weekday import Weekday

CONFIG_DIRECTORY_PATH = Path(__file__).parents[1] / "config" / "cities"


app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
cache = CityDataCache()


@app.get("/cities")
def cities() -> dict[str, CityConfiguration]:
    city_configuration_by_id: dict[str, CityConfiguration] = {}

    for file in filter(lambda x: x.is_file(), CONFIG_DIRECTORY_PATH.iterdir()):
        try:
            city_configuration_by_id[file.stem] = CityConfiguration.model_validate_json(
                file.read_text()
            )
        except ValidationError as exc:
            logger.exception(f"Invalid configuration file: {file.name}", exc_info=exc)
            raise HTTPException(500, "Invalid configuration files")

    return city_configuration_by_id


@app.get("/cities/{city_id}")
def get_city_data(city_id: str, weekday: str | None = None) -> ResponseCityData:
    day = Weekday.get_current_weekday(weekday)

    if not (file_path := CONFIG_DIRECTORY_PATH / f"{city_id}.json").is_file():
        raise HTTPException(404, "City not found")

    city_daily_schedule = f"{city_id}_{day.value}"
    if cache.is_cache_fresh(city_daily_schedule):
        logger.info(f"Loading data from cache for {city_daily_schedule}")
        return cache.load_cached_data(city_daily_schedule)

    try:
        city_configuration = CityConfiguration.from_path(file_path)
        city_data_builder = CityDataBuilder(city_configuration, day)
        return cache.store_and_return(
            city_daily_schedule,
            tram_track_graph=city_data_builder.tram_track_graph_data,
            tram_trips=city_data_builder.tram_trips_data,
        )

    except Exception as exc:
        logger.exception(
            f"Failed to build city data for {city_daily_schedule}", exc_info=exc
        )

        try:
            return cache.load_cached_data(city_daily_schedule)
        except Exception as inner:
            logger.exception(
                f"Cache loading failed for {city_daily_schedule}", exc_info=inner
            )

        raise HTTPException(422, f"Data processing for {city_daily_schedule} failed.")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
