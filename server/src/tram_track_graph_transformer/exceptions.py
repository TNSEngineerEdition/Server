class TrackDirectionChangeError(Exception):
    """
    Exception raised when a change in track direction is detected
    at a node where such a change is not allowed.
    """

    def __init__(self, node_id: int):
        self.node_id = node_id
        super().__init__(f"Track direction change in node {node_id}")
