from datetime import date
from enum import StrEnum


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @classmethod
    def get_current(cls):
        return list(cls)[date.today().weekday()]

    @classmethod
    def get_by_value_with_default(cls, weekday: str | None):
        if weekday is None:
            return cls.get_current()

        try:
            return cls(weekday.lower())
        except ValueError:
            raise ValueError(
                f"Invalid weekday: {weekday}. Must be one of: {list(map(str, cls))}"
            )
