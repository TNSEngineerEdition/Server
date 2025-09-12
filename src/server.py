import logging
import os
from datetime import date as d

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from city_data_builder import CityConfiguration, CityDataBuilder
from city_data_cache import CachedCityDates, CityDataCache, ResponseCityData
from tram_stop_mapper import Weekday

app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
city_data_cache = CityDataCache()


@app.get("/cities")
def cities() -> dict[str, CachedCityDates]:
    try:
        return city_data_cache.get_all_cached_dates()
    except ValidationError:
        raise HTTPException(500, "Invalid configuration files")


@app.get("/cities/{city_id}")
def get_city_data(
    city_id: str, weekday: str | None = None, date: str | None = None
) -> ResponseCityData:
    if date is not None and weekday is not None:
        raise HTTPException(400, "Provide either date or weekday")

    if date and (cached_date := city_data_cache.get(city_id, date)) is not None:
        return cached_date
    if date:
        raise HTTPException(
            404, f"City date for {city_id} not found in cache for {date}"
        )

    today_date_flag = weekday is None and date is None
    today_date: str = d.today().strftime("%Y-%m-%d")
    try:
        weekday_enum: Weekday = Weekday.get_by_value_with_default(weekday)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if today_date_flag:
        if today_cached_data := city_data_cache.get(city_id, today_date):
            return today_cached_data

    if (city_configuration := CityConfiguration.get_by_city_id(city_id)) is None:
        raise HTTPException(404, f"City {city_id} not found")

    try:
        city_data_builder = CityDataBuilder(city_configuration, weekday_enum)
        return city_data_cache.build_and_store(
            city_id, today_date, today_date_flag, city_data_builder
        )
    except Exception as exc:
        logger.exception(
            f"Failed to build city data for city {city_id} for weekday {weekday_enum}",
            exc_info=exc,
        )

    raise HTTPException(500, f"Data processing for {city_id} failed")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
