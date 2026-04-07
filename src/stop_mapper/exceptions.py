import overpy

from stop_mapper.stop_mapping_errors import StopMappingErrors


class StopMappingBuildError(ValueError):
    """
    Failure to build correct mapping of GTFS stops to OSM nodes.
    """

    def __init__(self, mapping_errors: StopMappingErrors) -> None:
        super().__init__(mapping_errors)

        self.mapping_errors = mapping_errors

    def __str__(self) -> str:
        return (
            f"Unable to build correct mapping of GTFS stops to OSM nodes.\n"
            f"{self.mapping_errors}"
        )


class StopNotFound(ValueError):
    """
    Stop with provided ID was not found in any mapping.
    """

    def __init__(self, missing_stop_id: str) -> None:
        super().__init__(missing_stop_id)

        self.missing_stop_id = missing_stop_id

    def __str__(self) -> str:
        return f"Stop {self.missing_stop_id} not found in any mapping."


class InvalidRelationTag(ValueError):
    """
    Provided tag of the provided relation is invalid.
    """

    def __init__(self, relation: overpy.Relation, *, tag_name: str, message: str):
        super().__init__(relation, tag_name, message)

        self.relation = relation
        self.tag_name = tag_name
        self.message = message

    def __str__(self) -> str:
        return f"Relation {self.relation.id} has invalid tag {self.tag_name}: {self.message}"
