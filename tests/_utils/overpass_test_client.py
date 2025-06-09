import overpy

from src.overpass_client import OverpassClient


class OverpassTestClient(OverpassClient):
    _TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node(around:0)["railway"="railway_crossing"];
    );
    out geom;
    """

    _TRAM_TRACK_CROSSINGS_EXCLUDING_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node(around:0)["railway"="railway_crossing"](if: {excluding_ids});
    );
    out geom;
    """

    _TRAM_TRACK_SWITCHES_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node(around:0)["railway"="switch"];
    );
    out geom;
    """

    _TRAM_STOPS_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area);
    );
    out geom;
    """

    _TRAM_STOPS_EXCLUDING_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        node["railway"="tram_stop"]["public_transport"="stop_position"](area.search_area)(if: {excluding_ids});
    );
    out geom;
    """

    @classmethod
    def get_tram_track_crossings(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_track_crossings_excluding(
        cls,
        area_name: str,
        excluding_ids: list[int],
    ) -> overpy.Result:
        query = cls._TRAM_TRACK_CROSSINGS_EXCLUDING_QUERY_TEMPLATE.format(
            area_name=area_name,
            excluding_ids=" && ".join(f"id() != {id}" for id in excluding_ids),
        )
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_track_switches(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_TRACK_SWITCHES_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_STOPS_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops_excluding(
        cls,
        area_name: str,
        excluding_ids: list[int],
    ):
        query = cls._TRAM_STOPS_EXCLUDING_QUERY_TEMPLATE.format(
            area_name=area_name,
            excluding_ids=" && ".join(f"id() != {id}" for id in excluding_ids),
        )
        return cls._OVERPASS.query(query)
