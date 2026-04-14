from typing import Annotated

from pydantic import BaseModel, Field

from city_data_builder.model.graph_model import (
    ResponseGraphNode,
    ResponseGraphStop,
)
from city_data_builder.model.trip_model import ResponseRoute


class ResponseCityData(BaseModel):
    graph: list[
        Annotated[
            ResponseGraphNode | ResponseGraphStop,
            Field(discriminator="node_type"),
        ]
    ]
    tram_routes: list[ResponseRoute]
    bus_routes: list[ResponseRoute] = Field(
        default_factory=list,
        json_schema_extra={"x-go-type-skip-optional-pointer": True},
    )
    paths: dict[int, dict[int, list[int]]] = Field(
        default_factory=dict,
        json_schema_extra={
            "x-go-type": "map[uint64]map[uint64][]uint64",
            "x-go-type-skip-optional-pointer": True,
        },
    )
