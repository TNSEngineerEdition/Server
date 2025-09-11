import datetime
import os
from pathlib import Path
from typing import ClassVar


class WeekdayDateResolver:
    CITIES_DIRECTORY_PATH: ClassVar[Path] = Path(
        os.environ.get("CITIES_DIRECTORY_PATH", "./cities")
    )

    @classmethod
    def get_newest_date_by_weekday(cls, city_id: str, weekday: str) -> None | str:
        city_path = cls.CITIES_DIRECTORY_PATH / city_id

        newest_date: str | None = None

        for city_date in city_path.iterdir():
            date = city_date.stem
            date_weekday = (
                datetime.datetime.strptime(date, "%Y-%m-%d")
                .date()
                .strftime("%A")
                .lower()
            )

            if date_weekday == weekday:
                if newest_date is None or date > newest_date:
                    newest_date = date

        return newest_date
