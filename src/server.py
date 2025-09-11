import datetime
import logging
import os
from datetime import date as d

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
def cities() -> dict[str, CityConfiguration]:
    try:
        return CityConfiguration.get_all()
    except ValidationError:
        raise HTTPException(500, "Invalid configuration files")


@app.get("/cities/{city_id}")
def get_city_data(
    city_id: str, weekday: str | None = None, date: str | None = None
) -> ResponseCityData:
    if date is not None and weekday is not None:
        raise HTTPException(400, "Provide either date or weekday")

    if weekday is None and date:
        weekday = (
            datetime.datetime.strptime(date, "%Y-%m-%d").date().strftime("%A").lower()
        )
    elif date is None and weekday:
        date = WeekdayDateResolver.get_newest_date_by_weekday(city_id, weekday)
    else:
        date = d.today().strftime("%Y-%m-%d")

    try:
        weekday_enum: Weekday = Weekday.get_by_value_with_default(weekday)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    date = str(date)

    if (
        city_configuration := CityConfiguration.get_by_city_id_and_date(city_id, date)
    ) is None:
        raise HTTPException(404, "City not found")

    print(city_configuration)

    print("przed budowaniem ")

    if not city_data_cache.get(city_id, date):
        print("budujemy dane")
        try:
            city_data_builder = CityDataBuilder(city_configuration, weekday_enum)
            city_data_cache.store(city_id, date, city_data_builder)
        except Exception as exc:
            logger.exception(
                f"Failed to build city data for city {city_id} and weekday {weekday_enum}",
                exc_info=exc,
            )

    if city_data := city_data_cache.get(city_id, date):
        print(city_data)
        return city_data

    raise HTTPException(500, f"Data processing for {city_id} failed")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=os.environ.get("APP_PORT", 8000),
    )
