import datetime
import logging
import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from city_data_builder import CityConfiguration, CityDataBuilder, ResponseCityData
from city_data_cache import CachedCityDates, CityDataCache
from tram_stop_mapper import Weekday

app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
city_data_cache = CityDataCache()


def validate_date(date: str | None = None) -> datetime.date | None:
    if date is None:
        return None
    try:
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: '{date}', expected YYYY-MM-DD",
        )


def validate_weekday(weekday: str | None = None) -> Weekday | None:
    if weekday is None:
        return None

    try:
        return Weekday.get_by_value(weekday)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/cities")
def cities() -> dict[str, CachedCityDates]:
    """
    Returns all available cities with their latest configurations and cached dates.
    """
    try:
        cities_config = CityConfiguration.get_all()
    except ValidationError:
        raise HTTPException(500, "Invalid configuration files")

    return {
        city_id: CachedCityDates(
            city_configuration=city_config,
            available_dates=city_data_cache.get_cached_dates(city_id),
        )
        for city_id, city_config in cities_config.items()
    }


@app.get("/cities/{city_id}")
def get_city_data(
    city_id: str,
    weekday: Weekday | None = Depends(validate_weekday),
    date: datetime.date | None = Depends(validate_date),
) -> ResponseCityData:
    """
    Returns processed data for a given city.

    - Without parameters: returns data for the current day
    (from cache if available, otherwise built and cached).
    - With `weekday`: builds and returns data for the given day of the week using currently available GTFS Schedule and OpenStreetMap data.
    - With `date`: returns cached data for the given date if available,
    otherwise responds with 404.
    - With both `weekday` and `date`: responds with 400, only one parameter is allowed.
    """
    if date is not None and weekday is not None:
        raise HTTPException(400, "Provide either date or weekday")

    if date:
        if cached_data := city_data_cache.get(city_id, date):
            return cached_data

        raise HTTPException(
            404, f"City data for {city_id} not found in cache for {date}"
        )

    is_today_build = weekday is None
    if is_today_build:
        date = datetime.date.today()
        weekday = Weekday.get_current()

        if today_cached_data := city_data_cache.get(city_id, date):
            return today_cached_data

    if (city_configuration := CityConfiguration.get_by_city_id(city_id)) is None:
        raise HTTPException(404, f"City {city_id} not found")

    assert weekday is not None
    assert date is not None

    try:
        city_data_builder = CityDataBuilder(city_configuration, weekday)
    except Exception as exc:
        logger.exception(
            "Failed to build city data for city %s for weekday %s",
            city_id,
            weekday
            exc_info=exc,
        )
        raise HTTPException(500, f"Data processing for {city_id} failed")

    city_data = city_data_builder.to_response_city_data()
    if is_today_build:
        city_data_cache.store(city_id, date, city_data)
    return city_data


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
