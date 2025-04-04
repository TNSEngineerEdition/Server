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
