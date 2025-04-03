from pydantic import BaseModel


class Node(BaseModel, frozen=True):
    id: int
    lat: float
    lon: float
    type: str
