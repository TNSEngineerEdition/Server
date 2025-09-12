from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field

from city_data_builder.city_configuration import CityConfiguration
from city_data_builder.model import (
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramRoute,
)


class ResponseCityData(BaseModel):
    tram_track_graph: list[ResponseGraphNode | ResponseGraphTramStop]
    tram_routes: list[ResponseTramRoute]
    last_updated: datetime = Field(default_factory=datetime.now)


class CachedCityDates(TypedDict):
    city_configuration: CityConfiguration
    available_dates: list[str]
