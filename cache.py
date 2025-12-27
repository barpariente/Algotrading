from datetime import datetime, timedelta
from typing import Any, Dict, Tuple


class SimpleCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.store: Dict[str, Tuple[Any, datetime]] = {}

    def get(self, key: str):
        if key not in self.store:
            return None

        value, timestamp = self.store[key]
        if datetime.utcnow() - timestamp > self.ttl:
            del self.store[key]
            return None

        return value

    def set(self, key: str, value: Any):
        self.store[key] = (value, datetime.utcnow())
