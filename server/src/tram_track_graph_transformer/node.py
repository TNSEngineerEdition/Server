from pydantic import BaseModel
from src.tram_track_graph_transformer.node_type import NodeType


class Node(BaseModel, frozen=True):
    """
    Represents a node in tram network graph.
    Attributes:
        id (int): Unique identifier of the node.
        lat (float): Geographic latitude of the node.
        lon (float): Geographic longitude of the node.
        type (NodeType): Type of the node (e.g., tram stop, switch).
    """

    id: int
    lat: float
    lon: float
    type: NodeType

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
