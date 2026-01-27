"""Tests for news cache module."""

import os
from unittest import mock

from quantsail_engine.cache.news import (
    InMemoryNewsCache,
    RedisNewsCache,
    get_news_cache,
    reset_news_cache,
)


def test_in_memory_cache_always_returns_false() -> None:
    """Test in-memory cache always returns False (no shared state)."""
    cache = InMemoryNewsCache()
    assert cache.is_negative_news_active() is False


def test_get_news_cache_returns_in_memory_without_redis() -> None:
    """Test get_news_cache returns in-memory cache when no Redis URL."""
    with mock.patch.dict(os.environ):
        os.environ.pop("REDIS_URL", None)

        reset_news_cache()
        cache = get_news_cache()

        assert isinstance(cache, InMemoryNewsCache)
    
    reset_news_cache()


def test_get_news_cache_returns_redis_with_url() -> None:
    """Test get_news_cache returns Redis cache when Redis URL provided."""
    with mock.patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6380/0"}):
        reset_news_cache()
        cache = get_news_cache()

        assert isinstance(cache, RedisNewsCache)

    reset_news_cache()


def test_redis_cache_is_negative_news_active() -> None:
    """Test Redis cache checks for news pause key."""
    # We need a real redis url for this test or mock it? 
    # The original test assumed it could connect or mocked it?
    # Original test:
    # redis_url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    # cache = RedisNewsCache(redis_url)
    
    # We should preserve that behavior but ensure env var doesn't leak
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    cache = RedisNewsCache(redis_url)

    # Clear any existing pause
    cache._client.delete("news:pause:negative")

    # Initially not active
    assert cache.is_negative_news_active() is False

    # Set a pause
    cache._client.set("news:pause:negative", "1")
    assert cache.is_negative_news_active() is True

    # Clean up
    cache._client.delete("news:pause:negative")
