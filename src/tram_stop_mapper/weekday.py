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
    def get_current_weekday(cls):
        return cls(datetime.datetime.now().strftime("%A").lower())

    @classmethod
    def get_weekday_by_value(cls, weekday: str):
        try:
            return cls(weekday.lower())
        except ValueError:
            raise ValueError(f"Invalid weekday: {weekday}. Must be one of {list(cls)}")
