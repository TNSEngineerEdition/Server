from datetime import datetime

from pydantic import BaseModel, Field

from city_data_builder.model import (
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramRoute,
)


class ResponseCityData(BaseModel):
    tram_track_graph: list[ResponseGraphNode | ResponseGraphTramStop]
    tram_routes: list[ResponseTramRoute]
    last_updated: datetime = Field(default_factory=datetime.now)
