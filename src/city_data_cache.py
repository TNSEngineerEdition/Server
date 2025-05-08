import json
from datetime import datetime, timedelta
from pathlib import Path


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

    def load_cached_data(self, city_id: str) -> dict:
        with open(self._get_path_to_cache(city_id), "r", encoding="utf-8") as f:
            data = json.load(f)
        data["last_updated"] = self._get_last_modified_timestamp(city_id)
        return data

    def save_to_cache(self, city_id: str, data: dict):
        def default(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            raise TypeError(f"{type(obj).__name__} is not JSON serializable")

        with open(self._get_path_to_cache(city_id), "w", encoding="utf-8") as f:
            json.dump(data, f, default=default)

    def _get_last_modified_timestamp(self, city_id: str) -> str | None:
        path = self._get_path_to_cache(city_id)
        return (
            datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            if path.exists()
            else None
        )
