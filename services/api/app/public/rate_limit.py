from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import redis
from fastapi import HTTPException, Request

from app.api.errors import error_detail


@dataclass(frozen=True)
class RateLimitConfig:
    per_minute: int
    window_seconds: int
    redis_url: str | None

    @staticmethod
    def from_env() -> "RateLimitConfig":
        """Load rate limit config from environment variables."""
        per_minute = int(os.environ.get("PUBLIC_RATE_LIMIT_PER_MIN", "60"))
        window_seconds = int(os.environ.get("PUBLIC_RATE_LIMIT_WINDOW_SECONDS", "60"))
        redis_url = os.environ.get("REDIS_URL")
        return RateLimitConfig(
            per_minute=per_minute, window_seconds=window_seconds, redis_url=redis_url
        )


class RateLimiter(Protocol):
    def allow(self, key: str) -> bool:
        """Return True if the key is within the rate limit."""
        ...


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        """Create an in-memory rate limiter for local development."""
        self._limit = config.per_minute
        self._window = config.window_seconds
        self._counts: dict[str, tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        """Return True if the key is within the rate limit window."""
        now = time.time()
        count, start = self._counts.get(key, (0, now))
        if now - start >= self._window:
            count, start = 0, now
        count += 1
        self._counts[key] = (count, start)
        return count <= self._limit


class RedisRateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        """Create a Redis-backed rate limiter."""
        if not config.redis_url:
            raise ValueError("REDIS_URL is required for Redis rate limiting.")
        self._limit = config.per_minute
        self._window = config.window_seconds
        self._client = redis.Redis.from_url(config.redis_url, decode_responses=True)

    def allow(self, key: str) -> bool:
        """Return True if the key is within the rate limit window."""
        window_id = int(time.time() // self._window)
        redis_key = f"rate:{key}:{window_id}"
        with self._client.pipeline() as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, self._window)
            count = pipe.execute()[0]
        return int(count) <= self._limit


def get_client_ip(request: Request) -> str:
    """Resolve the client IP from request headers or connection info."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", maxsplit=1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    """Return the configured rate limiter implementation."""
    config = RateLimitConfig.from_env()
    if config.redis_url:
        return RedisRateLimiter(config)
    return InMemoryRateLimiter(config)


def reset_rate_limiter() -> None:
    """Clear the cached rate limiter (used in tests)."""
    get_rate_limiter.cache_clear()


def enforce_rate_limit(request: Request) -> None:
    """Raise 429 if the request exceeds the configured rate limit."""
    limiter = get_rate_limiter()
    key = get_client_ip(request)
    if not limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail=error_detail("RATE_LIMITED", "Public rate limit exceeded."),
        )
