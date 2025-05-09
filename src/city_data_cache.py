from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from src.city_data_builder.model import ResponseGraphNode, ResponseTramTrip


class ResponseCityData(BaseModel):
    tram_track_graph: list[ResponseGraphNode]
    tram_trips: list[ResponseTramTrip]
    last_updated: datetime = Field(default_factory=lambda: datetime.now())


class CityDataCache:
    def __init__(
        self,
        cache_dir: Path = Path(__file__).parents[1] / "cached_data",
        ttl_hours: int = 24,
    ):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path_to_cache(self, city_id: str) -> Path:
        return self.cache_dir / f"{city_id}.json"

    def is_cache_fresh(self, city_id: str) -> bool:
        if not (path := self._get_path_to_cache(city_id)).exists():
            return False

        timedelta_since_last_update = datetime.now() - datetime.fromtimestamp(
            path.stat().st_mtime
        )

        return timedelta_since_last_update < self.ttl

    def load_cached_data(self, city_id: str) -> ResponseCityData:
        return ResponseCityData.model_validate_json(
            self._get_path_to_cache(city_id).read_text()
        )

    def store_and_return(
        self,
        city_id: str,
        tram_track_graph: list[ResponseGraphNode],
        tram_trips: list[ResponseTramTrip],
    ) -> ResponseCityData:
        data = ResponseCityData(
            tram_track_graph=tram_track_graph,
            tram_trips=tram_trips,
        )

        self._get_path_to_cache(city_id).write_text(data.model_dump_json())

        return data
