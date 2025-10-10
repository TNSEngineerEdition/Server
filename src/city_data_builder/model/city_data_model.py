from typing import Annotated

from pydantic import BaseModel, Field

from city_data_builder.model.tram_track_graph_model import (
    ResponseGraphNode,
    ResponseGraphTramStop,
)
from city_data_builder.model.tram_trip_model import ResponseTramRoute


class ResponseCityData(BaseModel):
    tram_track_graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphTramStop,
            Field(discriminator="node_type"),
        ]
    ]
    tram_routes: list[ResponseTramRoute]
