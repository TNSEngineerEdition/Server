from typing import Annotated

from pydantic import BaseModel, Field

from city_data_builder.model.graph_model import (
    ResponseGraphNode,
    ResponseGraphStop,
)
from city_data_builder.model.trip_model import ResponseRoute


class ResponseCityData(BaseModel):
    tram_track_graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphStop,
            Field(discriminator="node_type"),
        ]
    ]
    tram_routes: list[ResponseRoute]
    bus_road_graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphStop,
            Field(discriminator="node_type"),
        ]
    ] = Field(default_factory=list)
    bus_routes: list[ResponseRoute] = Field(default_factory=list)
