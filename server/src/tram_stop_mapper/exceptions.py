from src.tram_stop_mapper.tram_stop_mapping_errors import TramStopMappingErrors


class TramStopMappingBuildError(ValueError):
    """
    Unable to build correct mapping of GTFS stops to OSM nodes.
    """

    def __init__(self, mapping_errors: TramStopMappingErrors):
        super().__init__(mapping_errors)

        self.mapping_errors = mapping_errors

    def __str__(self):
        return f"{self.__doc__.strip()}\n{self.mapping_errors}"


class TramStopMappingUnknownNodeException(ValueError):
    """
    While performing mapping of GTFS stops to OSM nodes, an unmapped GTFS stop_id appeared.
    """

    def __init__(self, gtfs_trip_id_to_osm_node_ids: dict[str, list[int | None]]):
        super().__init__(gtfs_trip_id_to_osm_node_ids)

        self.gtfs_trip_id_to_osm_node_ids = gtfs_trip_id_to_osm_node_ids

    def __str__(self):
        trips_by_gtfs_trip_id: list[str] = []
        for gtfs_trip_id, osm_node_ids in self.gtfs_trip_id_to_osm_node_ids.items():
            osm_node_ids_as_str = ", ".join(map(str, osm_node_ids))
            trips_by_gtfs_trip_id.append(f"{gtfs_trip_id}: {osm_node_ids_as_str}")

        return "\n".join([self.__doc__.strip(), *trips_by_gtfs_trip_id])
