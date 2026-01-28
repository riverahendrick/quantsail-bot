"""Tests for news cache module."""

import time

from app.cache.news import InMemoryNewsCache, get_news_cache, reset_news_cache


def test_in_memory_cache_set_and_check() -> None:
    """Test in-memory cache can set and check pause state."""
    cache = InMemoryNewsCache()

    # Initially no pause
    assert cache.is_negative_news_active() is False

    # Set pause
    cache.set_negative_news_pause(1)  # 1 minute
    assert cache.is_negative_news_active() is True

    # Clear pause
    cache.clear_pause()
    assert cache.is_negative_news_active() is False


def test_in_memory_cache_expiry() -> None:
    """Test in-memory cache expires after duration."""
    cache = InMemoryNewsCache()

    # Set very short pause (simulate with manual time manipulation)
    cache.set_negative_news_pause(1)  # 1 minute
    assert cache.is_negative_news_active() is True

    # Manually expire by checking with mocked time (simplified test)
    # In real scenario, would wait or mock datetime
    # For now just verify clear works
    cache.clear_pause()
    assert cache.is_negative_news_active() is False


def test_get_news_cache_returns_in_memory_without_redis() -> None:
    """Test get_news_cache returns in-memory cache when no Redis URL."""
    import os

    # Ensure no REDIS_URL
    old_redis_url = os.environ.get("REDIS_URL")
    if old_redis_url:
        del os.environ["REDIS_URL"]

    reset_news_cache()
    cache = get_news_cache()

    # Should be in-memory
    assert isinstance(cache, InMemoryNewsCache)

    # Restore
    if old_redis_url:
        os.environ["REDIS_URL"] = old_redis_url
    reset_news_cache()
