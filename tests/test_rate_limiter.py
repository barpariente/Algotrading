from datetime import datetime, timedelta
from models import RateLimitConfig
from rate_limiter import RateLimiter


def test_allows_first_call():
    limiter = RateLimiter(RateLimitConfig(per_second=1, per_hour=10, per_day=100))
    assert limiter.allow("x", datetime.utcnow()) is True


def test_blocks_second_call_same_second():
    limiter = RateLimiter(RateLimitConfig(per_second=1, per_hour=10, per_day=100))
    now = datetime.utcnow()
    assert limiter.allow("x", now) is True
    assert limiter.allow("x", now) is False


def test_allows_call_in_next_second():
    limiter = RateLimiter(RateLimitConfig(per_second=1, per_hour=10, per_day=100))
    now = datetime.utcnow()
    assert limiter.allow("x", now) is True
    assert limiter.allow("x", now + timedelta(seconds=1)) is True
