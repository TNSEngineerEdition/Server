from city_configuration import GTFSConfiguration


class MissingGTFSPackage(Exception):
    """
    GTFS Schedule file couldn't be downloaded from the provided URL.
    """

    def __init__(self, config: GTFSConfiguration) -> None:
        super().__init__(
            f"GTFS Schedule file couldn't be downloaded from URL: {config.file_url}"
        )


class InvalidGTFSPackage(ValueError):
    """
    Provided GTFS package contains invalid data.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

        self.message = message

    def __str__(self) -> str:
        return f"Invalid GTFS data: {self.message}"
