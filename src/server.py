import datetime
import logging
import os
from zipfile import BadZipFile, ZipFile

import overpy
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

from city_data_builder import CityConfiguration, CityDataBuilder, ResponseCityData
from city_data_cache import CachedCityDates, CityDataCache
from tram_stop_mapper import (
    GTFSPackage,
    TramStopMappingBuildError,
    TramStopNotFound,
    Weekday,
)

app = FastAPI()
app.add_middleware(GZipMiddleware)

logger = logging.getLogger(__name__)
city_data_cache = CityDataCache()


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


def _get_city_data_by_date(city_id: str, date: datetime.date) -> ResponseCityData:
    if cached_data := city_data_cache.get(city_id, date):
        return cached_data

    raise HTTPException(404, f"City data for {city_id} not found in cache for {date}")


def _get_city_data_by_weekday(
    city_id: str, weekday: Weekday, custom_gtfs_package: GTFSPackage | None = None
) -> ResponseCityData:
    if (city_configuration := CityConfiguration.get_by_city_id(city_id)) is None:
        raise HTTPException(404, f"City {city_id} not found")

    try:
        city_data_builder = CityDataBuilder(
            city_configuration, weekday, custom_gtfs_package=custom_gtfs_package
        )
    except TramStopMappingBuildError as exc:
        raise HTTPException(500, str(exc))
    except overpy.exception.OverpassGatewayTimeout as exc:
        raise HTTPException(500, f"Overpass gateway timeout: {str(exc)}")
    except Exception as exc:
        logger.exception(
            "Failed to build city data for city %s for weekday %s",
            city_id,
            weekday,
            exc_info=exc,
        )
        raise HTTPException(500, f"Data processing for {city_id} failed")

    try:
        return city_data_builder.to_response_city_data()
    except TramStopNotFound as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to build response data for city %s for weekday %s",
            city_id,
            weekday,
            exc_info=exc,
        )
        raise HTTPException(500, f"Data processing for {city_id} failed")


def _get_city_data_today(city_id: str) -> ResponseCityData:
    today = datetime.date.today()
    if cached := city_data_cache.get(city_id, today):
        return cached

    data = _get_city_data_by_weekday(city_id, Weekday.get_current())
    city_data_cache.store(city_id, today, data)
    return data


@app.get("/cities/{city_id}")
def get_city_data(
    city_id: str,
    weekday: Weekday | None = Query(None),
    date: datetime.date = Query(None),
) -> ResponseCityData:
    """
    Returns tram track graph and tram routes data for the given city.

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
        return _get_city_data_by_date(city_id, date)

    if weekday:
        return _get_city_data_by_weekday(city_id, weekday)

    return _get_city_data_today(city_id)


def _validate_custom_schedule_file(custom_schedule_file: UploadFile) -> GTFSPackage:
    if custom_schedule_file.content_type != "application/zip":
        raise HTTPException(
            status_code=400, detail="Custom schedule file must be a ZIP file"
        )

    try:
        zip_file = ZipFile(custom_schedule_file.file)
    except BadZipFile:
        raise HTTPException(422, detail="File is not a ZIP file")

    if (invalid_file := zip_file.testzip()) is not None:
        raise HTTPException(status_code=422, detail=f"Invalid file: {invalid_file}")

    try:
        return GTFSPackage.from_zip_file(zip_file)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/cities/{city_id}")
def get_city_data_with_custom_schedule(
    city_id: str,
    weekday: Weekday = Query(default_factory=Weekday.get_current),
    custom_gtfs_package: GTFSPackage = Depends(_validate_custom_schedule_file),
) -> ResponseCityData:
    """
    Returns tram track graph and tram routes data for the given city.
    Uses custom GTFS package to determine tram routes.
    """

    return _get_city_data_by_weekday(city_id, weekday, custom_gtfs_package)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
