import overpy


class OverpassClient:
    _OVERPASS = overpy.Overpass()

    _RELATIONS_STOPS_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    out geom;
    """

    _RELATIONS_STOPS_NODES_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        relation["route"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
        node(id:{custom_node_ids})(area.search_area);
    );
    out geom;
    """

    _GET_TRAM_STOPS_AND_RAILWAYS_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    out geom;
    """

    _GET_TRAM_STOPs_AND_RAILWAYS_COORDINATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    way["railway"="tram"](area.search_area)->.tram_ways;
    node(w.tram_ways);
    out geom;
    """

    _GET_TRACK_GEOMETRY = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
    way["railway"="tram"](area.search_area);
    relation["railway"="tram"](area.search_area);
    );
    out body;
    >;
    out skel qt;
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
    def get_tram_stops_and_crossroads(cls, area_name: str):
        query = cls._GET_TRAM_STOPS_AND_RAILWAYS_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops_and_crossroads_coordinate(cls, area_name: str):
        query = cls._GET_TRAM_STOPs_AND_RAILWAYS_COORDINATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_track_geometry(cls, area_name: str):
        query = cls._GET_TRACK_GEOMETRY.format(area_name=area_name)
        return cls._OVERPASS.query(query)
