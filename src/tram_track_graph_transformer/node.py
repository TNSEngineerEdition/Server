from typing import Optional

from pydantic import BaseModel, Field

from tram_track_graph_transformer.node_type import NodeType


class Node(BaseModel):
    """
    Represents a node in tram network graph.
    Attributes:
        id (int): Unique identifier of the node.
        lat (float): Geographic latitude of the node.
        lon (float): Geographic longitude of the node.
        type (NodeType): Type of the node (e.g., tram stop, switch).
        name (Optional[str]): The name of the tram stop, set only when type == NodeType.TRAM_STOP.
    """

    id: int = Field(frozen=True)
    lat: float
    lon: float
    type: NodeType
    name: Optional[str] = None

    @property
    def coordinates(self):
        return (self.lat, self.lon)

    def __eq__(self, other):
        match other:
            case Node():
                return self.id == other.id
            case int():
                return self.id == other
            case _:
                return False

    def __hash__(self):
        return hash(self.id)
