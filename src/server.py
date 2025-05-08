import logging
import os
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from src.city_data_builder import CityConfiguration, CityDataBuilder
from src.city_data_cache import CityDataCache

CONFIG_DIRECTORY_PATH = Path(__file__).parents[1] / "config" / "cities"


app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
cache = CityDataCache()


@app.get("/cities")
def cities():
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
def get_city_data(city_id: str):
    if not (file_path := CONFIG_DIRECTORY_PATH / f"{city_id}.json").is_file():
        raise HTTPException(404, "City not found")

    if cache.is_cache_fresh(city_id):
        logger.info(f"Loading data from cache for {city_id}")
        return cache.load_cached_data(city_id)

    try:
        city_configuration = CityConfiguration.from_path(file_path)
        city_data_builder = CityDataBuilder(city_configuration)
        response_data = {
            "tram_track_graph": city_data_builder.tram_track_graph_data,
            "tram_trips": city_data_builder.tram_trips_data,
            "last_updated": datetime.now().isoformat(),
        }
        cache.save_to_cache(city_id, response_data)
        return response_data

    except Exception as exc:
        logger.exception(f"Failed to build city data for {city_id}", exc_info=exc)

        try:
            return cache.load_cached_data(city_id)
        except Exception as inner:
            logger.exception(f"Cache loading failed for {city_id}", exc_info=inner)

        raise HTTPException(422, "Data processing for {city_id} failed.")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
