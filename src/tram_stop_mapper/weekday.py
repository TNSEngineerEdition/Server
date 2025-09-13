from datetime import date
from enum import StrEnum
from typing import Optional


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @classmethod
    def get_current(cls) -> Optional["Weekday"]:
        return list(cls)[date.today().weekday()]

    @classmethod
    def get_by_value(cls, weekday: str | None) -> Optional["Weekday"]:
        if weekday is None:
            return None

        try:
            return cls(weekday.lower())
        except ValueError:
            raise ValueError(
                f"Invalid weekday: {weekday}. Must be one of: {list(map(str, cls))}"
            )
