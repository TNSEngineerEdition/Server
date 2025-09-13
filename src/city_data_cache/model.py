import datetime

from pydantic import BaseModel

from city_data_builder.city_configuration import CityConfiguration


class CachedCityDates(BaseModel):
    city_configuration: CityConfiguration
    available_dates: list[datetime.date]
