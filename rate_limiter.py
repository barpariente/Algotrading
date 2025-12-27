from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    def __init__(self, per_second, per_hour, per_day):
        self.limits = per_second, per_hour, per_day
        self.calls = defaultdict(list)

    def allow(self, key: str, now: datetime) -> bool:
        sec, hour, day = self.limits
        times = [t for t in self.calls[key] if t > now - timedelta(days=1)]
        self.calls[key] = times

        if sum(t > now - timedelta(seconds=1) for t in times) >= sec:
            return False
        if sum(t > now - timedelta(hours=1) for t in times) >= hour:
            return False
        if len(times) >= day:
            return False

        self.calls[key].append(now)
        return True
