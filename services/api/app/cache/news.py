"""News cache for circuit breaker pause state."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Protocol

import redis


class NewsCache(Protocol):
    """Protocol for news cache implementations."""

    def set_negative_news_pause(self, minutes: int) -> None:
        """Set a negative news pause for the specified duration in minutes."""
        ...

    def is_negative_news_active(self) -> bool:
        """Check if negative news pause is currently active."""
        ...

    def clear_pause(self) -> None:
        """Clear the news pause state."""
        ...


class InMemoryNewsCache:
    """In-memory news cache for local development."""

    def __init__(self) -> None:
        """Create an in-memory news cache."""
        self._pause_until: datetime | None = None

    def set_negative_news_pause(self, minutes: int) -> None:
        """Set a negative news pause for the specified duration in minutes."""
        from datetime import timedelta

        self._pause_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    def is_negative_news_active(self) -> bool:
        """Check if negative news pause is currently active."""
        if self._pause_until is None:
            return False
        now = datetime.now(timezone.utc)
        if now >= self._pause_until:
            self._pause_until = None
            return False
        return True

    def clear_pause(self) -> None:
        """Clear the news pause state."""
        self._pause_until = None


class RedisNewsCache:
    """Redis-backed news cache."""

    def __init__(self, redis_url: str) -> None:
        """Create a Redis-backed news cache."""
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key = "news:pause:negative"

    def set_negative_news_pause(self, minutes: int) -> None:
        """Set a negative news pause for the specified duration in minutes."""
        # Set key with TTL (expires automatically)
        self._client.setex(self._key, minutes * 60, "1")

    def is_negative_news_active(self) -> bool:
        """Check if negative news pause is currently active."""
        return bool(self._client.get(self._key))

    def clear_pause(self) -> None:
        """Clear the news pause state."""
        self._client.delete(self._key)


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
