class TrackDirectionChangeError(Exception):
    """
    Exception raised when a change in track direction is detected
    at a node that is not permanent node.
    """

    def __init__(self, start_node_id: int, node_id: int):
        self.node_id = node_id
        self.start_node_id = start_node_id
        super().__init__(
            f"Track from permanent node {start_node_id} "
            f"changes direction at non-permanent node {node_id}."
        )


class NoPathFoundError(Exception):
    def __init__(self, start: int, end: int):
        super().__init__(f"No path found between stops: {start} -> {end}")


class PathTooLongError(Exception):
    def __init__(
        self, start: int, end: int, actual_distance: float, allowed_distance: float
    ):
        super().__init__(
            f"Path too long: {start} -> {end} "
            f"distance: {actual_distance:.1f} > allowed: {allowed_distance:.1f}"
        )


class NodeNotFoundError(Exception):
    def __init__(self, node_id: int):
        super().__init__(f"Node with id {node_id} not found in the graph.")
