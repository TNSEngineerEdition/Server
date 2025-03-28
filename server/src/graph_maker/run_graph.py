from graph_maker.city_data_downloader import CityDataDownloader
from graph_maker.create_graph import NetworkGraph


def main():
    city = "Kraków"

    downloader = CityDataDownloader(city)
    ways, stops, coords, geometry = downloader.get_data()

    g = NetworkGraph(
        ways_data=ways,
        stops_data=stops,
        coords_data=coords,
        geometry_data=geometry,
        max_distance=25,
    )
    g.create_graph()
    g.visualize_graph(map_filename="graph_map_krk.html")


if __name__ == "__main__":
    main()
