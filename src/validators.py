import datetime
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile

from tram_stop_mapper import GTFSPackage, Weekday


def validate_date(date: str | None = None) -> datetime.date | None:
    if date is None:
        return None
    try:
        return datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: '{date}', expected YYYY-MM-DD",
        )


def validate_weekday(weekday: str | None = None) -> Weekday | None:
    if weekday is None:
        return None

    try:
        return Weekday.get_by_value(weekday)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def validate_custom_schedule_file(custom_schedule_file: UploadFile) -> GTFSPackage:
    if custom_schedule_file.content_type != "application/zip":
        raise HTTPException(
            status_code=400, detail="Custom schedule file must be a ZIP file"
        )

    try:
        zip_file = ZipFile(custom_schedule_file.file)
    except BadZipFile:
        raise HTTPException(422, detail="File is not a ZIP file")

    if (invalid_file := zip_file.testzip()) is not None:
        raise HTTPException(status_code=422, detail=f"Invalid file: {invalid_file}")

    try:
        return GTFSPackage.from_zip_file(zip_file)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
