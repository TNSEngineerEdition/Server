from pydantic import BaseModel


class CityConfiguration(BaseModel):
    osm_area_name: str
    gtfs_url: str
    ignored_gtfs_lines: list[str]
    custom_osm_stop_nodes: dict[str, int]
