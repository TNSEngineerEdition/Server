from typing import Annotated

from pydantic import BaseModel, Field

from city_data_builder.model.graph_model import (
    ResponseGraphNode,
    ResponseGraphStop,
)
from city_data_builder.model.tram_trip_model import ResponseTramRoute


class ResponseCityData(BaseModel):
    tram_track_graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphStop,
            Field(discriminator="node_type"),
        ]
    ]
    tram_routes: list[ResponseTramRoute]
    bus_road_graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphStop,
            Field(discriminator="node_type"),
        ]
    ] = Field(default_factory=list)
    paths: dict[int, dict[int, list[int]]] = Field(default_factory=dict)
