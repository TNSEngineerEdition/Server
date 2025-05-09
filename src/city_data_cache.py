import json
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from src.city_data_builder.model import ResponseGraphNode, ResponseTramTrip


class ResponseCityData(BaseModel):
    tram_track_graph: list[ResponseGraphNode]
    tram_trips: list[ResponseTramTrip]
    last_updated: str = datetime.now().isoformat()


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
        path = self._get_path_to_cache(city_id)
        if not path.exists():
            return False
        return datetime.now() - datetime.fromtimestamp(path.stat().st_mtime) < self.ttl

    def load_cached_data(self, city_id: str) -> ResponseCityData:
        with open(self._get_path_to_cache(city_id), "r", encoding="utf-8") as f:
            data = json.load(f)
        return ResponseCityData(**data)

    def store_and_return(
        self,
        city_id: str,
        tram_track_graph: list[ResponseGraphNode],
        tram_trips: list[ResponseTramTrip],
    ) -> ResponseCityData:
        def default(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            raise TypeError(f"{type(obj).__name__} is not JSON serializable")

        data = ResponseCityData(
            tram_track_graph=tram_track_graph,
            tram_trips=tram_trips,
            last_updated=datetime.now().isoformat(),
        )

        with open(self._get_path_to_cache(city_id), "w", encoding="utf-8") as f:
            json.dump(data, f, default=default)

        return data
