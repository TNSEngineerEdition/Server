from typing import Any

import overpy
from cachetools import cached, TTLCache

from city_configuration import TransitType


class OverpassClient:
    _OVERPASS = overpy.Overpass()

    _RELATIONS_AND_STOPS_CACHE: TTLCache[Any, overpy.Result] = TTLCache(128, 15 * 60)
    _TRAM_STOPS_AND_TRACKS_CACHE: TTLCache[Any, overpy.Result] = TTLCache(128, 15 * 60)

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
    @cached(_TRAM_STOPS_AND_TRACKS_CACHE)
    def get_tram_stops_and_tracks(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_STOPS_AND_TRACKS_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
