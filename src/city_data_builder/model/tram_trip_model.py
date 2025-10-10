import re
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseTramTripStop(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(json_schema_extra={"x-go-type": "uint64", "x-go-name": "ID"})
    time: int = Field(json_schema_extra={"x-go-type": "uint"})


class ResponseTramTrip(BaseModel):
    model_config = ConfigDict(frozen=True)

    trip_head_sign: str
    stops: list[ResponseTramTripStop]


class ResponseTramRoute(BaseModel):
    _HEX_COLOR_REGEX: ClassVar[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F]{6}$")
    _DEFAULT_BACKGROUND_COLOR: ClassVar[str] = "366DF2"
    _DEFAULT_TEXT_COLOR: ClassVar[str] = "FFFFFF"

    model_config = ConfigDict(frozen=True)

    name: str
    background_color: str
    text_color: str
    trips: list[ResponseTramTrip] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: Any) -> str:
        return str(value)

    @field_validator("background_color", mode="before")
    @classmethod
    def validate_background_color(cls, value: Any) -> str:
        if isinstance(value, str) and cls._HEX_COLOR_REGEX.match(value):
            return value.upper()

        return cls._DEFAULT_BACKGROUND_COLOR

    @field_validator("text_color", mode="before")
    @classmethod
    def validate_text_color(cls, value: Any) -> str:
        if isinstance(value, str) and cls._HEX_COLOR_REGEX.match(value):
            return value.upper()

        return cls._DEFAULT_TEXT_COLOR
