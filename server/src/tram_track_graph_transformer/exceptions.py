class TrackDirectionChangeError(Exception):
    def __init__(self, node_id: int):
        self.node_id = node_id
        super().__init__(f"Track direction change in node {node_id}")
