"""News cache checker for engine circuit breaker."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol


class NewsCache(Protocol):
    """Protocol for news cache implementations."""

    def is_negative_news_active(self) -> bool:
        """Check if negative news pause is currently active."""
        ...


class InMemoryNewsCache:
    """In-memory news cache for local development (always False)."""

    def is_negative_news_active(self) -> bool:
        """Always returns False - no shared state in memory."""
        return False


class RedisNewsCache:
    """Redis-backed news cache reader."""

    def __init__(self, redis_url: str) -> None:
        """Create a Redis-backed news cache reader."""
        import redis

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key = "news:pause:negative"

    def is_negative_news_active(self) -> bool:
        """Check if negative news pause is currently active."""
        return bool(self._client.get(self._key))


@lru_cache(maxsize=1)
def get_news_cache() -> NewsCache:
    """Return the configured news cache implementation."""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return RedisNewsCache(redis_url)
    return InMemoryNewsCache()


def reset_news_cache() -> None:
    """Clear the cached news cache (used in tests)."""
    get_news_cache.cache_clear()
