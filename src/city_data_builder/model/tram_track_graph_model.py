from abc import ABC
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseGraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(json_schema_extra={"x-go-type": "uint64", "x-go-name": "ID"})
    distance: float
    azimuth: float
    max_speed: float

    @field_validator("distance", "azimuth", "max_speed", mode="after")
    @classmethod
    def round_to_4_decimal_places(cls, value: float) -> float:
        return round(value, 4)


class BaseGraphNode(BaseModel, ABC):
    model_config = ConfigDict(frozen=True)

    id: int = Field(json_schema_extra={"x-go-type": "uint64", "x-go-name": "ID"})
    lat: float
    lon: float
    neighbors: dict[int, ResponseGraphEdge]
    node_type: Literal["node", "stop"]

    @field_validator("lat", "lon", mode="after")
    @classmethod
    def round_to_7_decimal_places(cls, value: float) -> float:
        return round(value, 7)


class ResponseGraphNode(BaseGraphNode):
    # Default factory hides default value in OpenAPI schema
    node_type: Literal["node"] = Field(default_factory=lambda: "node")


class ResponseGraphTramStop(BaseGraphNode):
    # Default factory hides default value in OpenAPI schema
    node_type: Literal["stop"] = Field(default_factory=lambda: "stop")

    name: str
    gtfs_stop_ids: list[str]
