from datetime import datetime, timedelta

from rate_limiter import RateLimiter
from models import RateLimitConfig

def test_allows_first_call():
    limiter = RateLimiter(
        RateLimitConfig(per_second=1, per_hour=10, per_day=100)
    )

    now = datetime.utcnow()
    assert limiter.allow("news_api", now) is True

def test_blocks_exceeding_per_second_limit():
    limiter = RateLimiter(
        RateLimitConfig(per_second=1, per_hour=10, per_day=100)
    )

    now = datetime.utcnow()

    assert limiter.allow("news_api", now) is True
    assert limiter.allow("news_api", now) is False

def test_allows_call_in_next_second():
    limiter = RateLimiter(
        RateLimitConfig(per_second=1, per_hour=10, per_day=100)
    )

    now = datetime.utcnow()

    assert limiter.allow("news_api", now) is True
    assert limiter.allow("news_api", now + timedelta(seconds=1)) is True

def test_blocks_exceeding_per_hour_limit():
    limiter = RateLimiter(
        RateLimitConfig(per_second=10, per_hour=2, per_day=100)
    )

    now = datetime.utcnow()

    assert limiter.allow("alpaca", now) is True
    assert limiter.allow("alpaca", now + timedelta(minutes=1)) is True
    assert limiter.allow("alpaca", now + timedelta(minutes=2)) is False

def test_separate_keys_have_separate_limits():
    limiter = RateLimiter(
        RateLimitConfig(per_second=1, per_hour=10, per_day=100)
    )

    now = datetime.utcnow()

    assert limiter.allow("news_api", now) is True
    assert limiter.allow("alpaca", now) is True

def test_blocks_exceeding_daily_limit():
    limiter = RateLimiter(
        RateLimitConfig(per_second=10, per_hour=10, per_day=2)
    )

    now = datetime.utcnow()

    assert limiter.allow("sentiment", now) is True
    assert limiter.allow("sentiment", now + timedelta(hours=1)) is True
    assert limiter.allow("sentiment", now + timedelta(hours=2)) is False

