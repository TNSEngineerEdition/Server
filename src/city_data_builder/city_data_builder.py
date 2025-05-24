from src.city_data_builder.city_configuration import CityConfiguration
from src.city_data_builder.model import (
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramTrip,
    ResponseTramTripStop,
)
from src.overpass_client import OverpassClient
from src.tram_stop_mapper import GTFSPackage, TramStopMapper, Weekday
from src.tram_track_graph_transformer import (
    Node,
    NodeType,
    TramTrackGraphInspector,
    TramTrackGraphTransformer,
)


class CityDataBuilder:
    def __init__(
        self,
        city_configuration: CityConfiguration,
        weekday: Weekday,
        max_distance_between_nodes: float = 5,
    ):
        self._city_configuration = city_configuration
        self._max_distance_between_nodes = max_distance_between_nodes
        self._weekday = weekday
        self._tram_stop_mapper = self._get_tram_stop_mapper()
        self._tram_track_graph = self._get_tram_track_graph()

    def _get_tram_stop_mapper(self):
        relations_and_stops = OverpassClient.get_relations_and_stops(
            self._city_configuration.osm_area_name,
            list(self._city_configuration.custom_stop_mapping.values()),
        )

        gtfs_package = GTFSPackage.from_url(self._city_configuration.gtfs_url)

        tram_stop_mapper = TramStopMapper(
            self._city_configuration, gtfs_package, relations_and_stops
        )

        return tram_stop_mapper

    def _get_tram_track_graph(self):
        tram_stops_and_tracks = OverpassClient.get_tram_stops_and_tracks(
            self._city_configuration.osm_area_name
        )

        tram_track_graph_transformer = TramTrackGraphTransformer(
            tram_stops_and_tracks,
            self._city_configuration,
        )

        tram_track_graph = tram_track_graph_transformer.densify_graph_by_max_distance(
            self._max_distance_between_nodes
        )

        tram_track_graph_inspector = TramTrackGraphInspector(tram_track_graph)
        for (
            start_stop_id,
            end_stop_id,
        ) in tram_track_graph_inspector.get_unique_tram_stop_pairs(
            self._tram_stop_mapper.stop_nodes_by_gtfs_trip_id
        ):
            tram_track_graph_inspector.check_path_viability(
                start_stop_id, end_stop_id, self._max_distance_between_nodes
            )

        return tram_track_graph

    @property
    def tram_track_graph_data(self):
        response_data_edge_by_source: dict[Node, list[ResponseGraphEdge]] = {
            node: [] for node in self._tram_track_graph.nodes
        }

        for source, dest, data in self._tram_track_graph.edges.data():
            response_data_edge_by_source[source].append(
                ResponseGraphEdge(
                    id=dest.id,
                    length=data["length"],
                    azimuth=data["azimuth"],
                    max_speed=data["max_speed"],
                )
            )

        result: list[ResponseGraphNode] = []
        for node in response_data_edge_by_source:
            if node.type == NodeType.TRAM_STOP:
                response_node = ResponseGraphTramStop(
                    id=node.id,
                    lat=node.lat,
                    lon=node.lon,
                    name=node.name or "",
                    neighbors=response_data_edge_by_source[node],
                    gtfs_stop_ids=list(
                        self._tram_stop_mapper.gtfs_stop_ids_by_node_id[node.id]
                    ),
                )
            else:
                response_node = ResponseGraphNode(
                    id=node.id,
                    lat=node.lat,
                    lon=node.lon,
                    neighbors=response_data_edge_by_source[node],
                )

            result.append(response_node)

        return result

    @property
    def tram_trips_data(self):
        trip_data_by_trip_id, trip_stops_data = (
            self._tram_stop_mapper.trip_data_and_stops_by_trip_id
        )

        return [
            ResponseTramTrip(
                route=str(trip_data["route_long_name"]),
                trip_head_sign=trip_data["trip_headsign"],
                stops=[
                    ResponseTramTripStop(id=node_id, time=stop_time)
                    for node_id, stop_time in trip_stops_data[trip_id]
                ],
            )
            for trip_id, trip_data in trip_data_by_trip_id.items()
            if (
                trip_id in trip_stops_data
                and self._weekday.value in trip_data.get("service_days")
            )
        ]
