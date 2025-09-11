import datetime as dt
import os
from pathlib import Path
from typing import ClassVar


class WeekdayDateResolver:
    CITIES_DIRECTORY_PATH: ClassVar[Path] = Path(
        os.environ.get("CITIES_DIRECTORY_PATH", "./cities")
    )

    @classmethod
    def _get_newest_date_by_weekday(cls, city_id: str, weekday: str) -> str:
        city_path = cls.CITIES_DIRECTORY_PATH / city_id

        newest_date: str | None = None

        for city_date in city_path.iterdir():
            date = city_date.stem
            date_weekday = (
                dt.datetime.strptime(date, "%Y-%m-%d").date().strftime("%A").lower()
            )

            if date_weekday == weekday:
                if newest_date is None or date > newest_date:
                    newest_date = date
        if newest_date is None:
            raise ValueError(
                f"No City Configuration found for city {city_id} with weekday {weekday}"
            )

        return newest_date

    @classmethod
    def get_date_and_weekday(
        cls, city_id: str, date: str | None, weekday: str | None
    ) -> tuple[str, str]:
        if weekday is None and date:
            weekday = dt.datetime.strptime(date, "%Y-%m-%d").date().strftime("%A")
        elif date is None and weekday:
            date = WeekdayDateResolver._get_newest_date_by_weekday(city_id, weekday)
        else:
            today = dt.date.today()
            date = today.strftime("%Y-%m-%d")
            weekday = today.strftime("%A").lower()
        return date, weekday.lower()
