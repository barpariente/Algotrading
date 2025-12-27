from datetime import datetime, timedelta
from collections import defaultdict
from models import RateLimitConfig


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.calls = defaultdict(list)

    def allow(self, key: str, now: datetime) -> bool:
        times = [
            t for t in self.calls[key]
            if t > now - timedelta(days=1)
        ]
        self.calls[key] = times

        if sum(t > now - timedelta(seconds=1) for t in times) >= self.config.per_second:
            return False

        if sum(t > now - timedelta(hours=1) for t in times) >= self.config.per_hour:
            return False

        if len(times) >= self.config.per_day:
            return False

        self.calls[key].append(now)
        return True
