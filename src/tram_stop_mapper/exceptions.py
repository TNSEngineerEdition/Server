from tram_stop_mapper.tram_stop_mapping_errors import TramStopMappingErrors


class TramStopMappingBuildError(ValueError):
    """
    Failure to build correct mapping of GTFS stops to OSM nodes.
    """

    def __init__(self, mapping_errors: TramStopMappingErrors):
        super().__init__(mapping_errors)

        self.mapping_errors = mapping_errors

    def __str__(self) -> str:
        return (
            f"Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            f"{self.mapping_errors}"
        )
