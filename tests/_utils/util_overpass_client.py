import overpy
<<<<<<<< HEAD:tests/_utils/util_overpass_client.py
<<<<<<< HEAD:tests/_utils/util_overpass_client.py
from src.overpass_client import OverpassClient


class OverpassTestClient(OverpassClient):
=======


class UtilOverpassClient:
    def __init__(self):
        self.overpass = overpy.Overpass()

>>>>>>> 986df59 (graph transformer tests remake, updated data freezing, updated city config):server/tests/_utils/util_overpass_client.py
========
from src.overpass_client import OverpassClient


class OverpassTestClient(OverpassClient):
>>>>>>>> eaf4a85 (updated fixtures, moved assets from frozen data):tests/_utils/overpass_test_client.py
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

<<<<<<<< HEAD:tests/_utils/util_overpass_client.py
<<<<<<< HEAD:tests/_utils/util_overpass_client.py
========
>>>>>>>> eaf4a85 (updated fixtures, moved assets from frozen data):tests/_utils/overpass_test_client.py
    @classmethod
    def get_tram_track_crossings(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
<<<<<<<< HEAD:tests/_utils/util_overpass_client.py

    @classmethod
    def get_tram_track_switches(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_TRACK_SWITCHES_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

    @classmethod
    def get_tram_stops(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_STOPS_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
=======
    def get_tram_track_crossings(self, area_name: str) -> overpy.Result:
        query = self._TRAM_TRACK_CROSSINGS_QUERY_TEMPLATE.format(area_name=area_name)
        return self.overpass.query(query)
========
>>>>>>>> eaf4a85 (updated fixtures, moved assets from frozen data):tests/_utils/overpass_test_client.py

    @classmethod
    def get_tram_track_switches(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_TRACK_SWITCHES_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)

<<<<<<<< HEAD:tests/_utils/util_overpass_client.py
    def get_tram_stops(self, area_name: str) -> overpy.Result:
        query = self._TRAM_STOPS_QUERY_TEMPLATE.format(area_name=area_name)
        return self.overpass.query(query)
>>>>>>> 986df59 (graph transformer tests remake, updated data freezing, updated city config):server/tests/_utils/util_overpass_client.py
========
    @classmethod
    def get_tram_stops(cls, area_name: str) -> overpy.Result:
        query = cls._TRAM_STOPS_QUERY_TEMPLATE.format(area_name=area_name)
        return cls._OVERPASS.query(query)
>>>>>>>> eaf4a85 (updated fixtures, moved assets from frozen data):tests/_utils/overpass_test_client.py
