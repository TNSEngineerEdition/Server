from overpass_client.overpass_client import OverpassClient


class CityDataDownloader:
    def __init__(self, city: str):
        self.city = city

    def get_data(self):
        return OverpassClient.get_tram_stops_and_tracks(self.city)
