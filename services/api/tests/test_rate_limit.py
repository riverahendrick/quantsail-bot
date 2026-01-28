from __future__ import annotations

import pytest

from app.public.rate_limit import RateLimitConfig, RedisRateLimiter


def test_redis_rate_limiter_requires_url() -> None:
    """Raise when Redis rate limiter is created without a URL."""
    config = RateLimitConfig(per_minute=1, window_seconds=60, redis_url=None)

    with pytest.raises(ValueError):
        RedisRateLimiter(config)
