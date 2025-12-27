import requests
from datetime import datetime
from cache import SimpleCache
from rate_limiter import RateLimiter
from agents import RateLimitConfig

price_cache = SimpleCache(ttl_seconds=60 * 60)  # 1 hour

rate_limiter = RateLimiter(
    RateLimitConfig(per_second=1, per_hour=50, per_day=500)
)

API_KEY = "YOUR_API_KEY"


def fetch_recent_prices(symbol: str, days: int = 5) -> list[float]:
    cache_key = f"prices:{symbol}:{days}"
    cached = price_cache.get(cache_key)
    if cached is not None:
        return cached

    if not rate_limiter.allow("price_api", datetime.utcnow()):
        raise RuntimeError("Rate limit exceeded")

    # Example API (pseudo)
    response = requests.get(
        "https://api.example.com/prices",
        params={"symbol": symbol, "days": days, "apikey": API_KEY},
        timeout=5,
    )
    response.raise_for_status()

    prices = response.json()["prices"]  # list[float]

    price_cache.set(cache_key, prices)
    return prices
