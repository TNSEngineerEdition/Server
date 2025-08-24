import overpy
from pydantic import BaseModel, ConfigDict, Field


class TramStopMappingErrors(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    missing_relations_for_lines: set[str] = Field(default_factory=set)
    nodes_with_conflict: dict[str, list[tuple[str | None, int]]] = Field(
        default_factory=dict
    )
    stops_without_mapping: set[str] = Field(default_factory=set)
    underutilized_relations: dict[overpy.Relation, list[str]] = Field(
        default_factory=dict
    )

    @property
    def _missing_relations_for_lines_error_message(self) -> str:
        return ", ".join(sorted(self.missing_relations_for_lines))

    @property
    def _nodes_with_conflict_error_message(self) -> str:
        return "\n".join(
            (
                f"{gtfs_stop_id}: {", ".join(
                    f"{stop_name} ({stop_id})"
                    for stop_name, stop_id in sorted(nodes, key=lambda x: x[1])
                )}"
            )
            for gtfs_stop_id, nodes in self.nodes_with_conflict.items()
        )

    @property
    def _stops_without_mapping_error_message(self) -> str:
        return ", ".join(sorted(self.stops_without_mapping))

    @property
    def _underutilized_relations_error_message(self) -> str:
        return "\n\n".join(
            f"Relation ID: {relation.id}\nStops of relation:\n{"\n".join(stops)}"
            for relation, stops in self.underutilized_relations.items()
        )

    def __str__(self) -> str:
        error_messages: list[str] = []

        if self.missing_relations_for_lines:
            error_messages.append(
                "Missing relations for lines: "
                + self._missing_relations_for_lines_error_message
            )

        if self.nodes_with_conflict:
            error_messages.append(
                "Nodes with conflict:\n" + self._nodes_with_conflict_error_message
            )

        if self.stops_without_mapping:
            error_messages.append(
                "Stops without mapping: " + self._stops_without_mapping_error_message
            )

        if self.underutilized_relations:
            error_messages.append(
                "Underutilized relations:\n"
                + self._underutilized_relations_error_message
            )

        return "\n\n".join(error_messages)

    def __bool__(self) -> bool:
        return bool(
            self.missing_relations_for_lines
            or self.nodes_with_conflict
            or self.stops_without_mapping
            or self.underutilized_relations
        )
