import os
from typing import Any

import overpy
from cachetools import cached, TTLCache

from city_configuration import TransitType
from overpass_client.retry_query import retry_query


class OverpassClient:
    _OVERPASS = overpy.Overpass()

    _CACHE_TTL = int(os.environ.get("OVERPASS_CACHE_TTL", 60 * 60))

    _RELATIONS_AND_STOPS_CACHE: TTLCache[Any, overpy.Result] = TTLCache(128, _CACHE_TTL)
    _TRAM_STOPS_AND_TRACKS_CACHE: TTLCache[Any, overpy.Result] = TTLCache(
        128, _CACHE_TTL
    )
    _WAY_GEOMETRY_CACHE: TTLCache[Any, overpy.Result] = TTLCache(128, _CACHE_TTL)

    _TRAM_RELATIONS_STOPS_QUERY_TEMPLATE = """
    [out:json][timeout:600];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    out geom;
    """

    _TRAM_RELATIONS_STOPS_NODES_QUERY_TEMPLATE = """
    [out:json][timeout:600];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        node(id:{custom_node_ids})(area.search_area);
    );
    out geom;
    """

    _BUS_RELATIONS_STOPS_QUERY_TEMPLATE = """
    [out:json][timeout:600];

    area["name"="{relation_area_name}"]->.relation_search_area;
    relation["type"="route"]["route"="bus"]["network"="{network}"](area.relation_search_area)->.relations;

    area["name"="{stop_area_name}"]->.stop_search_area;
    node["public_transport"="stop_position"]["bus"="yes"](area.stop_search_area)->.stops;

    (.relations; .stops;);
    out geom;
    """

    _BUS_RELATIONS_STOPS_NODES_QUERY_TEMPLATE = """
    [out:json][timeout:600];

    area["name"="{relation_area_name}"]->.relation_search_area;
    relation["type"="route"]["route"="bus"]["network"="{network}"](area.relation_search_area)->.relations;

    area["name"="{stop_area_name}"]->.stop_search_area;
    (
        node["public_transport"="stop_position"]["bus"="yes"](area.stop_search_area);
        node(id:{custom_node_ids})(area.stop_search_area);
    )->.stops;

    (.relations; .stops;);
    out geom;
    """

    _TRAM_STOPS_AND_TRACKS_TEMPLATE = """
    [out:json][timeout:600];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    (._; >;);
    out geom;
    """

    _BUS_ROADS_TEMPLATE = """
    [out:json][timeout:600];

    area["name"="{area_name}"]->.search_area;

    (
    rel(area.search_area)["type"="route"]["route"="bus"]["network"="{network}"];
    )->.candidate_routes;

    rel.candidate_routes["ref"~"^(Telebus|LR[0-9]+|[0-9]{{2,3}})$"]->.line_routes;

    way(r.line_routes)
    ["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|service|living_street|busway|road)$"]
    ["area"!="yes"]->.bus_ways;

    (
    .bus_ways;
    node(w.bus_ways);
    );

    (._; >;);
    out geom;
    """

    @classmethod
    def _get_tram_relations_and_stops_query(
        cls, area_name: str, custom_node_ids: tuple[int]
    ) -> str:
        if custom_node_ids:
            return cls._TRAM_RELATIONS_STOPS_NODES_QUERY_TEMPLATE.format(
                area_name=area_name,
                custom_node_ids=", ".join(map(str, custom_node_ids)),
            )

        return cls._TRAM_RELATIONS_STOPS_QUERY_TEMPLATE.format(area_name=area_name)

    @classmethod
    def _get_bus_relations_and_stops_query(
        cls,
        network: str,
        relation_area_name: str,
        stop_area_name: str,
        custom_node_ids: tuple[int],
    ) -> str:
        if custom_node_ids:
            return cls._BUS_RELATIONS_STOPS_NODES_QUERY_TEMPLATE.format(
                relation_area_name=relation_area_name,
                stop_area_name=stop_area_name,
                network=network,
                custom_node_ids=", ".join(map(str, custom_node_ids)),
            )

        return cls._BUS_RELATIONS_STOPS_QUERY_TEMPLATE.format(
            relation_area_name=relation_area_name,
            stop_area_name=stop_area_name,
            network=network,
        )

    @classmethod
    @cached(_RELATIONS_AND_STOPS_CACHE)
    @retry_query(10)
    def get_relations_and_stops(
        cls,
        transit_type: TransitType,
        network: str,
        relation_area_name: str,
        stop_area_name: str,
        custom_node_ids: tuple[int],
    ) -> overpy.Result:
        match transit_type:
            case TransitType.TRAM:
                query = cls._get_tram_relations_and_stops_query(
                    relation_area_name, custom_node_ids
                )
            case TransitType.BUS:
                query = cls._get_bus_relations_and_stops_query(
                    network,
                    relation_area_name,
                    stop_area_name,
                    custom_node_ids,
                )
            case _:
                raise ValueError("Unknown transit type")

        return cls._OVERPASS.query(query)

    @classmethod
    @cached(_WAY_GEOMETRY_CACHE)
    @retry_query(10)
    def get_way_geometry(
        cls,
        transit_type: TransitType,
        network: str | None,
        area_name: str,
    ) -> overpy.Result:
        match transit_type:
            case TransitType.TRAM:
                query = cls._TRAM_STOPS_AND_TRACKS_TEMPLATE.format(area_name=area_name)
            case TransitType.BUS:
                query = cls._BUS_ROADS_TEMPLATE.format(
                    area_name=area_name, network=network
                )
            case _:
                raise ValueError("Unknown transit type")

        return cls._OVERPASS.query(query)
