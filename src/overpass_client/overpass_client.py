import overpy


class OverpassClient:
    _OVERPASS = overpy.Overpass()

    _RELATIONS_STOPS_QUERY_TEMPLATE = """
    [out:json][timeout:600];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    out geom;
    """

    _RELATIONS_STOPS_NODES_QUERY_TEMPLATE = """
    [out:json][timeout:600];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        node(id:{custom_node_ids})(area.search_area);
    );
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
    rel(area.search_area)["type"="route"]["route"="bus"]["network"="KMK"];
    rel(area.search_area)["type"="route"]["route"="bus"]["network"="Komunikacja Miejska w Krakowie"];
    rel(area.search_area)["type"="route"]["route"="bus"]["network"="ZTP w Krakowie"];
    rel(area.search_area)["type"="route"]["route"="bus"]["network:short"="KMK"];
    rel(area.search_area)["type"="route"]["route"="bus"]["operator"="Zarząd Transportu Publicznego w Krakowie"];
    rel(area.search_area)["type"="route"]["route"="bus"]["operator"="ZTP Kraków"];
    rel(area.search_area)["type"="route"]["route"="bus"]["operator"="MPK Kraków"];
    rel(area.search_area)["type"="route"]["route"="bus"]["operator"="kmk"];
    )->.candidate_routes;

    rel.candidate_routes["ref"~"^(Telebus|LR[0-9]+|[0-9]{{2,3}})$"]->.line_routes;

    way(r.line_routes)
    ["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|service|living_street|busway|road)$"]
    ["area"!="yes"]->.bus_ways;

    (
    .line_routes;
    .bus_ways;
    node(w.bus_ways);
    );

    (._; >;);
    out geom;
    """

    @classmethod
    def get_relations_and_stops(
        cls, area_name: str, custom_node_ids: list[int]
    ) -> overpy.Result:
        if custom_node_ids:
            query = cls._RELATIONS_STOPS_NODES_QUERY_TEMPLATE.format(
                area_name=area_name,
                custom_node_ids=", ".join(map(str, custom_node_ids)),
            )
        else:
            query = cls._RELATIONS_STOPS_QUERY_TEMPLATE.format(area_name=area_name)

        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops_and_tracks(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_STOPS_AND_TRACKS_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_bus_roads(cls, area_name: str) -> overpy.Result:
        query = cls._BUS_ROADS_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
