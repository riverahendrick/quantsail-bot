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
    # Mock the redis client so we don't need a real connection
    with mock.patch("redis.Redis.from_url") as mock_redis_cls:
        # Setup the mock client
        mock_client = mock.Mock()
        mock_redis_cls.return_value = mock_client
        
        # Configure get behavior
        # First call returns None (False), Second call returns "1" (True)
        mock_client.get.side_effect = [None, "1"]
        
        redis_url = "redis://localhost:6380/0"
        cache = RedisNewsCache(redis_url)

        # 1. Clear existing (calls delete) - we just verify call
        cache._client.delete("news:pause:negative")
        mock_client.delete.assert_called_with("news:pause:negative")

        # 2. Initially not active (get returns None)
        assert cache.is_negative_news_active() is False

        # 3. Set a pause (calls set) - we verify call
        cache._client.set("news:pause:negative", "1")
        mock_client.set.assert_called_with("news:pause:negative", "1")
        
        # 4. Now active (get returns "1")
        assert cache.is_negative_news_active() is True

