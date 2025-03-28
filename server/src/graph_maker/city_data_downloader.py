from model import (
    NodeCoordinate,
    TrackGeometry,
    TrackGeometryFeature,
    TramStop,
    Way,
)
from overpass_client.overpass_client import OverpassClient


class CityDataDownloader:
    def __init__(self, city: str):
        self.city = city

    def get_data(self):
        result = OverpassClient.get_tram_stops_and_crossroads(self.city)

        ways_data = [
            Way(
                id=way.id,
                nodes=way._node_ids,
                tags=way.tags,
            )
            for way in result.ways
        ]

        tram_stops_data = [
            TramStop(
                id=node.id,
                lat=float(node.lat),
                lon=float(node.lon),
                name=node.tags.get("name"),
            )
            for node in result.nodes
            if node.tags.get("railway") == "tram_stop"
        ]

        result_coords = OverpassClient.get_tram_stops_and_crossroads_coordinate(
            self.city
        )
        nodes_data = [
            NodeCoordinate(
                id=node.id,
                lat=float(node.lat),
                lon=float(node.lon),
            )
            for node in result_coords.nodes
        ]

        result_tracks = OverpassClient.get_track_geometry(self.city)
        features = [
            TrackGeometryFeature(
                type="Feature",
                properties={"id": way.id, "tags": way.tags},
                geometry={
                    "type": "LineString",
                    "coordinates": [
                        (float(node.lon), float(node.lat)) for node in way.nodes
                    ],
                },
            )
            for way in result_tracks.ways
        ]

        geojson = TrackGeometry(type="FeatureCollection", features=features)

        return ways_data, tram_stops_data, nodes_data, geojson
