import overpy


class UtilOverpassClient:
    def __init__(self):
        self.overpass = overpy.Overpass()

    _TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE = """
    [out:json];
    area["name"="{area_name}"]->.search_area;
    (
        way["railway"="tram"](area.search_area);
        node(around:0)["railway"="railway_crossing"];
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

    def get_tram_track_crossings(self, area_name: str) -> overpy.Result:
        query = self._TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE.format(area_name=area_name)
        return self.overpass.query(query)

    def get_tram_track_switches(self, area_name: str) -> overpy.Result:
        query = self._TRAM_TRACK_SWITCHES_QUERY_TEMPLATE.format(area_name=area_name)
        return self.overpass.query(query)

    def get_tram_stops(self, area_name: str) -> overpy.Result:
        query = self._TRAM_STOPS_QUERY_TEMPLATE.format(area_name=area_name)
        return self.overpass.query(query)
