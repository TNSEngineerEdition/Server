import networkx as nx

from city_data_builder.city_configuration import CityConfiguration
from city_data_builder.model import (
    ResponseCityData,
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseGraphTramStop,
    ResponseTramRoute,
    ResponseTramTrip,
    ResponseTramTripStop,
)
from overpass_client import OverpassClient
from tram_stop_mapper import GTFSPackage, TramStopMapper, Weekday
from tram_track_graph_transformer import (
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
        *,
        custom_gtfs_package: GTFSPackage | None = None,
        max_distance_between_nodes: float = 5.0,
    ):
        self._city_configuration = city_configuration
        self._weekday = weekday
        self._custom_gtfs_package = custom_gtfs_package
        self._max_distance_between_nodes = max_distance_between_nodes

        self._tram_stop_mapper = self._get_tram_stop_mapper()
        self._tram_track_graph = self._get_tram_track_graph()

    def _get_tram_stop_mapper(self) -> TramStopMapper:
        custom_node_ids: list[int] = []
        for item in self._city_configuration.custom_stop_mapping.values():
            if isinstance(item, int):
                custom_node_ids.append(item)
            else:
                custom_node_ids.extend(filter(lambda x: x is not None, item))  # type: ignore[arg-type]

        relations_and_stops = OverpassClient.get_relations_and_stops(
            self._city_configuration.osm_area_name,
            custom_node_ids,
        )

        gtfs_package = GTFSPackage.from_url(self._city_configuration.gtfs_url)

        tram_stop_mapper = TramStopMapper(
            self._city_configuration, gtfs_package, relations_and_stops
        )

        return tram_stop_mapper

    def _get_tram_track_graph(self) -> "nx.DiGraph[Node]":
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

    def to_response_city_data(self) -> ResponseCityData:
        return ResponseCityData(
            tram_track_graph=self.tram_track_graph_data,
            tram_routes=self.tram_routes_data,
        )

    def _get_response_node(
        self, node: Node, neighbors: dict[int, ResponseGraphEdge]
    ) -> ResponseGraphNode | ResponseGraphTramStop:
        if node.type == NodeType.TRAM_STOP:
            return ResponseGraphTramStop(
                id=node.id,
                lat=node.lat,
                lon=node.lon,
                name=node.name or "",
                neighbors=neighbors,
                gtfs_stop_ids=sorted(
                    self._tram_stop_mapper.gtfs_stop_ids_by_node_id[node.id]
                ),
            )

        return ResponseGraphNode(
            id=node.id,
            lat=node.lat,
            lon=node.lon,
            neighbors=neighbors,
        )

    @property
    def tram_track_graph_data(self) -> list[ResponseGraphNode | ResponseGraphTramStop]:
        response_data_edge_by_source: dict[Node, dict[int, ResponseGraphEdge]] = {
            node: {} for node in self._tram_track_graph.nodes
        }

        for source, dest, data in self._tram_track_graph.edges.data():
            response_data_edge_by_source[source][dest.id] = ResponseGraphEdge(
                id=dest.id,
                distance=data["distance"],
                azimuth=data["azimuth"],
                max_speed=data["max_speed"],
            )

        return [
            self._get_response_node(node, neighbors)
            for node, neighbors in response_data_edge_by_source.items()
        ]

    @property
    def tram_routes_data(self) -> list[ResponseTramRoute]:
        trip_stops_by_trip_id = self._tram_stop_mapper.get_trip_stops_by_trip_id(
            self._custom_gtfs_package
        )

        gtfs_package = self._custom_gtfs_package or self._tram_stop_mapper.gtfs_package

        routes_by_route_id = {
            str(route_id): ResponseTramRoute(
                name=route_data["route_long_name"],
                background_color=route_data["route_color"],
                text_color=route_data["route_text_color"],
            )
            for route_id, route_data in gtfs_package.routes.iterrows()
        }

        for (
            trip_id,
            trip_data,
        ) in gtfs_package.get_trips_for_weekday(self._weekday):
            if trip_id not in trip_stops_by_trip_id:
                continue

            routes_by_route_id[trip_data["route_id"]].trips.append(
                ResponseTramTrip(
                    trip_head_sign=trip_data["trip_headsign"],
                    stops=[
                        ResponseTramTripStop(id=stop.stop_id, time=stop.time)
                        for stop in trip_stops_by_trip_id[trip_id]
                    ],
                )
            )

        return list(filter(lambda x: x.trips, routes_by_route_id.values()))
