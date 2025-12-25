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
    def from_date(cls, date: datetime.date) -> "Weekday":
        return list(cls)[date.weekday()]

    @classmethod
    def get_current(cls) -> "Weekday":
        return cls.from_date(datetime.date.today())
