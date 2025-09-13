import datetime
from typing import TypedDict

from city_data_builder.city_configuration import CityConfiguration


class CachedCityDates(TypedDict):
    city_configuration: CityConfiguration
    available_dates: list[datetime.date]
