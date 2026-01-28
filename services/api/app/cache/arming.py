"""Arming token cache for live trading."""

import os
import secrets
from typing import Protocol

import redis


class ArmingCache(Protocol):
    """Protocol for arming cache."""

    def create_token(self, ttl_seconds: int = 30) -> str:
        """Create and store a short-lived arming token."""
        ...

    def verify_and_consume_token(self, token: str) -> bool:
        """Verify token exists and delete it (one-time use)."""
        ...


class InMemoryArmingCache:
    """In-memory cache for testing."""

    def __init__(self) -> None:
        self._token: str | None = None

    def create_token(self, ttl_seconds: int = 30) -> str:
        token = secrets.token_hex(16)
        self._token = token
        return token

    def verify_and_consume_token(self, token: str) -> bool:
        if self._token == token:
            self._token = None
            return True
        return False


class RedisArmingCache:
    """Redis-backed arming cache."""

    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = "bot:arming_token:"

    def create_token(self, ttl_seconds: int = 30) -> str:
        token = secrets.token_hex(16)
        # Store token as key to allow multiple concurrent arming attempts if needed (unlikely but safe)
        # Value is timestamp or dummy
        self._client.set(f"{self._key_prefix}{token}", "1", ex=ttl_seconds)
        return token

    def verify_and_consume_token(self, token: str) -> bool:
        key = f"{self._key_prefix}{token}"
        # Lua script to check and delete atomically
        script = """
        if redis.call("EXISTS", KEYS[1]) == 1 then
            redis.call("DEL", KEYS[1])
            return 1
        else
            return 0
        end
        """
        result = self._client.eval(script, 1, key)  # type: ignore
        return bool(result)


from functools import lru_cache

@lru_cache(maxsize=1)
def get_arming_cache() -> ArmingCache:
    """Return the configured arming cache."""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return RedisArmingCache(redis_url)
    return InMemoryArmingCache()
