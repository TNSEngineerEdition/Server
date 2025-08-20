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

    @classmethod
    def get_relations_and_stops(cls, area_name: str, custom_node_ids: list[int]):
        if custom_node_ids:
            query = cls._RELATIONS_STOPS_NODES_QUERY_TEMPLATE.format(
                area_name=area_name,
                custom_node_ids=", ".join(map(str, custom_node_ids)),
            )
        else:
            query = cls._RELATIONS_STOPS_QUERY_TEMPLATE.format(area_name=area_name)

        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops_and_tracks(cls, area_name: str):
        query = cls._TRAM_STOPS_AND_TRACKS_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
