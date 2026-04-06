import datetime
from collections import defaultdict
from collections.abc import Generator

import networkx as nx
import overpy

from city_configuration import CityConfiguration, GTFSConfiguration, TransitType
from city_data_builder.model import (
    ResponseCityData,
    ResponseGraphEdge,
    ResponseGraphNode,
    ResponseGraphStop,
    ResponseRoute,
    ResponseTrip,
    ResponseTripStop,
)
from graph_transformer import (
    GraphInspector,
    GraphTransformer,
    Node,
    NodeType,
    PathTooLongError,
)
from gtfs import GTFSPackage, GTFSPackageStore, Weekday
from overpass_client import OverpassClient
from stop_mapper import StopIDAndTime, StopMapper


class CityDataBuilder:
    def __init__(
        self,
        city_configuration: CityConfiguration,
        weekday: Weekday,
        gtfs_package_store: GTFSPackageStore,
        *,
        is_today: bool,
        custom_gtfs_package: GTFSPackage | None = None,
        max_distance_between_nodes: float = 5.0,
    ) -> None:
        self._city_configuration = city_configuration
        self._weekday = weekday
        self._gtfs_package_store = gtfs_package_store
        self._is_today = is_today
        self._custom_gtfs_package = custom_gtfs_package
        self._max_distance_between_nodes = max_distance_between_nodes

        self._stop_mappers = self._get_stop_mappers()
        self._tram_track_graph = self._get_tram_track_graph()
        self._bus_road_graph = self._get_bus_road_graph()

        self._paths = self._get_paths()

    def _get_gtfs_package_for_gtfs_config(
        self, gtfs_config: GTFSConfiguration
    ) -> GTFSPackage:
        return self._custom_gtfs_package or self._stop_mappers[gtfs_config].gtfs_package

    def _get_stop_mappers(self) -> dict[GTFSConfiguration, StopMapper]:
        stop_mappers: dict[GTFSConfiguration, StopMapper] = {}

        for gtfs_config in self._city_configuration.gtfs_configurations:
            custom_node_ids: list[int] = []

            for custom_mapping in gtfs_config.custom_stop_mapping.values():
                if isinstance(custom_mapping, int):
                    custom_node_ids.append(custom_mapping)
                else:
                    custom_node_ids.extend(
                        node_id for node_id in custom_mapping if node_id is not None
                    )

            relations_and_stops = OverpassClient.get_relations_and_stops(
                gtfs_config.transit_type,
                self._city_configuration.osm_network,
                self._city_configuration.osm_relations_area_name,
                self._city_configuration.osm_stops_area_name,
                tuple(custom_node_ids),
            )

            gtfs_package = self._gtfs_package_store.load_gtfs_package(gtfs_config)

            stop_mapper = StopMapper(
                gtfs_config,
                gtfs_package,
                relations_and_stops,
                self._city_configuration.ignored_osm_relations,
            )

            stop_mappers[gtfs_config] = stop_mapper

        return stop_mappers

    def _get_graph(
        self, overpy_result: overpy.Result, error_enable: bool
    ) -> "nx.DiGraph[Node]":
        graph_transformer = GraphTransformer(
            overpy_result,
            self._city_configuration,
        )

        return graph_transformer.densify_graph_by_max_distance(
            self._max_distance_between_nodes, error_enable
        )

    def _get_tram_track_graph(self) -> "nx.DiGraph[Node]":
        tram_stops_and_tracks = OverpassClient.get_way_geometry(
            TransitType.TRAM,
            self._city_configuration.osm_network,
            self._city_configuration.osm_relations_area_name,
        )

        return self._get_graph(tram_stops_and_tracks, True)

    def _get_bus_road_graph(self) -> "nx.DiGraph[Node]":
        bus_roads = OverpassClient.get_way_geometry(
            TransitType.BUS,
            network=self._city_configuration.osm_network,
            area_name=self._city_configuration.osm_relations_area_name,
        )

        return self._get_graph(bus_roads, False)

    def _get_paths(self) -> dict[int, dict[int, list[int]]]:
        paths: defaultdict[int, dict[int, list[int]]] = defaultdict(dict)

        tram_track_graph_inspector = GraphInspector(self._tram_track_graph)
        bus_road_graph_inspector = GraphInspector(self._bus_road_graph)

        path_too_long_exceptions: list[PathTooLongError] = []
        for stop_mapper in self._stop_mappers.values():
            match stop_mapper.gtfs_configuration.transit_type:
                case TransitType.TRAM:
                    graph_inspector = tram_track_graph_inspector
                case TransitType.BUS:
                    graph_inspector = bus_road_graph_inspector
                case _ as transit_type:
                    raise ValueError(f"Unexpected transit type: {transit_type}")

            unique_stop_pairs = graph_inspector.get_unique_stop_pairs(
                stop_mapper.stop_nodes_by_gtfs_trip_id
            )

            for start_stop_id, end_stop_id in unique_stop_pairs:
                try:
                    path = graph_inspector.get_viable_path(
                        start_stop_id,
                        end_stop_id,
                        self._city_configuration.custom_stop_pair_ratio_map.get(
                            (start_stop_id, end_stop_id),
                            self._city_configuration.max_distance_ratio,
                        ),
                    )
                except PathTooLongError as exc:
                    path_too_long_exceptions.append(exc)
                    continue

                paths[start_stop_id][end_stop_id] = [node.id for node in path]

        if path_too_long_exceptions:
            raise ExceptionGroup("Some paths are too long", path_too_long_exceptions)

        return dict(paths)

    def to_response_city_data(self) -> ResponseCityData:
        return ResponseCityData(
            tram_track_graph=self.tram_track_graph_data,
            tram_routes=self.tram_routes_data,
            bus_road_graph=self.bus_road_graph_data,
            bus_routes=self.bus_routes_data,
            paths=self._paths,
        )

    def _get_stop_node(
        self,
        stop_mapper: StopMapper,
        node: Node,
        neighbors: dict[int, ResponseGraphEdge],
    ) -> ResponseGraphStop:
        gtfs_stop_ids = sorted(stop_mapper.gtfs_stop_ids_by_node_id.get(node.id, set()))

        if node.type == NodeType.TRAM_STOP or node.type == NodeType.BUS_STOP:
            stop_name = node.name or ""
        elif gtfs_stop_ids:
            stop_row = stop_mapper.gtfs_package.stops.loc[gtfs_stop_ids[0]]
            stop_name = str(stop_row["stop_name"])
        else:
            stop_name = node.name or ""

        stop_group_name = (
            stop_mapper.gtfs_package.get_stop_group_name_by_stop_ids(
                stop_mapper._gtfs_config.stop_group_name_pattern, gtfs_stop_ids
            )
            if gtfs_stop_ids
            else None
        )

        return ResponseGraphStop(
            id=node.id,
            lat=node.lat,
            lon=node.lon,
            name=stop_name,
            stop_group_name=stop_group_name,
            neighbors=neighbors,
            gtfs_stop_ids=gtfs_stop_ids,
        )

    def _get_response_node(
        self, node: Node, neighbors: dict[int, ResponseGraphEdge]
    ) -> ResponseGraphNode | ResponseGraphStop:
        for stop_mapper in self._stop_mappers.values():
            if node.id in stop_mapper.gtfs_stop_ids_by_node_id:
                return self._get_stop_node(stop_mapper, node, neighbors)

        if node.type == NodeType.TRAM_STOP or node.type == NodeType.BUS_STOP:
            return ResponseGraphStop(
                id=node.id,
                lat=node.lat,
                lon=node.lon,
                name=node.name or "",
                stop_group_name=None,
                neighbors=neighbors,
                gtfs_stop_ids=[],
            )

        return ResponseGraphNode(
            id=node.id,
            lat=node.lat,
            lon=node.lon,
            neighbors=neighbors,
        )

    @property
    def tram_track_graph_data(self) -> list[ResponseGraphNode | ResponseGraphStop]:
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
    def bus_road_graph_data(self) -> list[ResponseGraphNode | ResponseGraphStop]:
        response_data_edge_by_source: dict[Node, dict[int, ResponseGraphEdge]] = {
            node: {} for node in self._bus_road_graph.nodes
        }

        for source, dest, data in self._bus_road_graph.edges.data():
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

    def _add_trips_to_routes(
        self,
        gtfs_package: GTFSPackage,
        trip_stops_by_trip_id: dict[str, list[StopIDAndTime]],
        routes_by_route_id: dict[str, ResponseRoute],
    ) -> None:
        service_ids = (
            gtfs_package.get_service_ids_for_date(datetime.date.today())
            if self._is_today
            else gtfs_package.service_ids_by_weekday[self._weekday]
        )

        for trip_id, trip_data in gtfs_package.get_trips_for_service_ids(service_ids):
            trip_stops = [
                ResponseTripStop(id=stop.stop_id, time=stop.time)
                for stop in trip_stops_by_trip_id.get(trip_id, [])
            ]
            if len(trip_stops) <= 1:
                continue

            route = routes_by_route_id[str(trip_data["route_id"])]

            trip_stop_ids = [stop.stop_id for stop in trip_stops_by_trip_id[trip_id]]
            variant = next(
                (
                    name
                    for name, stops in route.variants.items()
                    if stops == trip_stop_ids
                ),
                None,
            )

            route.trips.append(
                ResponseTrip(
                    trip_head_sign=trip_data["trip_headsign"],
                    variant=variant,
                    stops=trip_stops,
                )
            )

    def _get_tram_routes_data_for_gtfs_config(
        self, gtfs_config: GTFSConfiguration
    ) -> Generator[ResponseRoute, None, None]:
        tram_stop_mapper = self._stop_mappers[gtfs_config]
        gtfs_package = self._get_gtfs_package_for_gtfs_config(gtfs_config)

        trip_stops_by_trip_id = tram_stop_mapper.get_trip_stops_by_trip_id(
            self._custom_gtfs_package
        )

        routes_by_route_id: dict[str, ResponseRoute] = {}
        for route_id, route_data in gtfs_package.routes.iterrows():
            route_name = str(route_data["route_short_name"])

            routes_by_route_id[str(route_id)] = ResponseRoute(
                name=route_name,
                background_color=route_data["route_color"],
                text_color=route_data["route_text_color"],
                variants=tram_stop_mapper.get_variants_for_route(
                    route_name, gtfs_package
                ),
            )

        self._add_trips_to_routes(
            gtfs_package,
            trip_stops_by_trip_id,
            routes_by_route_id,
        )

        yield from filter(lambda x: x.trips, routes_by_route_id.values())

    def _get_bus_routes_data_for_gtfs_config(
        self, gtfs_config: GTFSConfiguration
    ) -> Generator[ResponseRoute, None, None]:
        bus_stop_mapper = self._stop_mappers[gtfs_config]
        gtfs_package = self._get_gtfs_package_for_gtfs_config(gtfs_config)

        trip_stops_by_trip_id = bus_stop_mapper.get_trip_stops_by_trip_id(
            self._custom_gtfs_package
        )

        routes_by_route_id: dict[str, ResponseRoute] = {}
        for route_id, route_data in gtfs_package.routes.iterrows():
            route_name = str(route_data["route_short_name"])

            routes_by_route_id[str(route_id)] = ResponseRoute(
                name=route_name,
                background_color=route_data["route_color"],
                text_color=route_data["route_text_color"],
                variants={},
            )

        self._add_trips_to_routes(
            gtfs_package,
            trip_stops_by_trip_id,
            routes_by_route_id,
        )

        yield from filter(lambda x: x.trips, routes_by_route_id.values())

    @property
    def tram_routes_data(self) -> list[ResponseRoute]:
        tram_routes: list[ResponseRoute] = []

        for gtfs_config in self._city_configuration.gtfs_configurations:
            if gtfs_config.transit_type == TransitType.TRAM:
                tram_routes.extend(
                    self._get_tram_routes_data_for_gtfs_config(gtfs_config)
                )

        return tram_routes

    @property
    def bus_routes_data(self) -> list[ResponseRoute]:
        bus_routes: list[ResponseRoute] = []
        for gtfs_config in self._city_configuration.gtfs_configurations:
            if gtfs_config.transit_type == TransitType.BUS:
                bus_routes.extend(
                    self._get_bus_routes_data_for_gtfs_config(gtfs_config)
                )

        return bus_routes
