import datetime
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
    def get_current_weekday(cls, weekday: str | None = None):
        if weekday is None:
            return cls(datetime.datetime.now().strftime("%A").lower())

        try:
            return cls(weekday.lower())
        except ValueError:
            raise ValueError(f"Invalid weekday: {weekday}. Must be one of {list(cls)}")
