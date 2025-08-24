import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from city_data_builder import CityConfiguration, CityDataBuilder
from city_data_cache import CityDataCache, ResponseCityData
from tram_stop_mapper import Weekday

app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
city_data_cache = CityDataCache()


@app.get("/cities")
def cities() -> dict[str, CityConfiguration]:
    try:
        return CityConfiguration.get_all()
    except ValidationError:
        raise HTTPException(500, "Invalid configuration files")


@app.get("/cities/{city_id}")
def get_city_data(city_id: str, weekday: str | None = None) -> ResponseCityData:
    try:
        weekday = Weekday.get_by_value_with_default(weekday)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if (city_configuration := CityConfiguration.get_by_city_id(city_id)) is None:
        raise HTTPException(404, "City not found")

    if not city_data_cache.is_fresh(city_id, weekday):
        try:
            city_data_builder = CityDataBuilder(city_configuration, weekday)
            city_data_cache.store(city_id, weekday, city_data_builder)
        except Exception as exc:
            logger.exception(
                f"Failed to build city data for city {city_id} and weekday {weekday}",
                exc_info=exc,
            )

    if city_data := city_data_cache.get(city_id, weekday):
        return city_data

    raise HTTPException(500, f"Data processing for {city_id} failed")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
