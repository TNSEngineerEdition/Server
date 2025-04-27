import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError
from src.city_data_builder import CityConfiguration, CityDataBuilder

CONFIG_DIRECTORY_PATH = Path(__file__).parents[1] / "config" / "cities"


app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)


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

    city_configuration = CityConfiguration.from_path(file_path)
    city_data_builder = CityDataBuilder(city_configuration)

    return {
        "tram_track_graph": city_data_builder.tram_track_graph_data,
        "tram_trips": city_data_builder.tram_trips_data,
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
