from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

from models import RateLimitConfig


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.calls: Dict[str, List[datetime]] = {}

    def allow(self, key: str, now: datetime) -> bool:
        history = self.calls.setdefault(key, [])

        one_second_ago = now - timedelta(seconds=1)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        history[:] = [t for t in history if t > one_day_ago]

        per_day = len([t for t in history if t > one_day_ago])
        per_hour = len([t for t in history if t > one_hour_ago])
        per_second = len([t for t in history if t > one_second_ago])

        if per_second >= self.config.per_second:
            return False
        if per_hour >= self.config.per_hour:
            return False
        if per_day >= self.config.per_day:
            return False

        history.append(now)
        return True
