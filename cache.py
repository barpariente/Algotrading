from __future__ import annotations
import os
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


class DiskCache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path_for_key(self, key: str) -> str:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._path_for_key(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            exp = payload.get("expires_at")
            if exp is not None and datetime.now(timezone.utc) > datetime.fromisoformat(exp):
                try:
                    os.remove(path)
                except OSError:
                    pass
                return None
            return payload["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        path = self._path_for_key(key)
        payload: Dict[str, Any] = {"value": value, "expires_at": None}
        if ttl_seconds is not None:
            payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
