import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from city_data_builder import CityConfiguration, CityDataBuilder
from city_data_cache import CityDataCache, ResponseCityData
from tram_stop_mapper import Weekday, WeekdayDateResolver

app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
city_data_cache = CityDataCache()


@app.get("/cities")
def cities() -> dict[str, dict[str, CityConfiguration]]:
    try:
        return city_data_cache.get_all()
    except ValidationError:
        raise HTTPException(500, "Invalid configuration files")


@app.get("/cities/{city_id}")
def get_city_data(
    city_id: str, weekday: str | None = None, date: str | None = None
) -> ResponseCityData:
    if date is not None and weekday is not None:
        raise HTTPException(400, "Provide either date or weekday")

    try:
        date_resolved, weekday_resolved = WeekdayDateResolver.get_date_and_weekday(
            city_id, date, weekday
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    try:
        weekday_enum: Weekday = Weekday.get_by_value(weekday_resolved)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if (
        city_configuration := CityConfiguration.get_by_city_id_and_date(
            city_id, date_resolved
        )
    ) is None:
        raise HTTPException(
            404, f"City {city_id} not found for {weekday_resolved} {date_resolved}"
        )

    if not city_data_cache.get(city_id, date_resolved):
        try:
            city_data_builder = CityDataBuilder(city_configuration, weekday_enum)
            city_data = city_data_cache.build_and_store(
                city_id, date_resolved, city_data_builder
            )
            return city_data
        except Exception as exc:
            logger.exception(
                f"Failed to build city data for city {city_id} for date {date_resolved} weekday {weekday_enum}",
                exc_info=exc,
            )

    if cached_city_data := city_data_cache.get(city_id, date_resolved):
        return cached_city_data

    raise HTTPException(500, f"Data processing for {city_id} failed")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
