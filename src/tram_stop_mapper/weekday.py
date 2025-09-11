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
    def get_by_value(cls, weekday: str) -> "Weekday":
        try:
            return cls(weekday.lower())
        except ValueError:
            raise ValueError(
                f"Invalid weekday: {weekday}. Must be one of: {list(map(str, cls))}"
            )
