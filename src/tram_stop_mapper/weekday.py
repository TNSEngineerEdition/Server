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
    def get_current(cls) -> "Weekday":
        return list(cls)[date.today().weekday()]
