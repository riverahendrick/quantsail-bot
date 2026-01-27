"""Tests for news pause integration in circuit breakers."""

from unittest.mock import patch

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.config.models import BotConfig


def test_news_pause_disabled_by_default(in_memory_db) -> None:
    """Test news pause is disabled by default in config."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig()
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    # News pause disabled by default
    assert config.breakers.news.enabled is False

    # Entries allowed even if news cache says paused
    with patch("quantsail_engine.breakers.manager.get_news_cache") as mock_cache:
        mock_cache.return_value.is_negative_news_active.return_value = True
        allowed, _ = manager.entries_allowed()
        # Still allowed because news.enabled=False
        assert allowed is True


def test_news_pause_blocks_entries_when_enabled(in_memory_db) -> None:
    """Test news pause blocks entries when enabled and active."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig(breakers=BotConfig.model_fields["breakers"].default_factory())
    config.breakers.news.enabled = True
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    with patch("quantsail_engine.breakers.manager.get_news_cache") as mock_cache:
        # Simulate active news pause
        mock_cache.return_value.is_negative_news_active.return_value = True

        allowed, reason = manager.entries_allowed()

        assert allowed is False
        assert reason == "negative news pause active"


def test_news_pause_allows_entries_when_not_active(in_memory_db) -> None:
    """Test entries allowed when news pause not active."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig(breakers=BotConfig.model_fields["breakers"].default_factory())
    config.breakers.news.enabled = True
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    with patch("quantsail_engine.breakers.manager.get_news_cache") as mock_cache:
        # No active news pause
        mock_cache.return_value.is_negative_news_active.return_value = False

        allowed, reason = manager.entries_allowed()

        assert allowed is True
        assert reason is None


def test_news_pause_exits_always_allowed(in_memory_db) -> None:
    """Test exits always allowed even with active news pause."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig(breakers=BotConfig.model_fields["breakers"].default_factory())
    config.breakers.news.enabled = True
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    with patch("quantsail_engine.breakers.manager.get_news_cache") as mock_cache:
        # Active news pause
        mock_cache.return_value.is_negative_news_active.return_value = True

        # Exits still allowed
        exits_allowed, reason = manager.exits_allowed()
        assert exits_allowed is True
        assert reason is None


def test_news_pause_combined_with_breakers(in_memory_db) -> None:
    """Test news pause works alongside other breakers."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig(breakers=BotConfig.model_fields["breakers"].default_factory())
    config.breakers.news.enabled = True
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    # Trigger a breaker
    manager.trigger_breaker("volatility", "Test", 30, {"atr": 2.0})

    with patch("quantsail_engine.breakers.manager.get_news_cache") as mock_cache:
        # Also active news pause
        mock_cache.return_value.is_negative_news_active.return_value = True

        allowed, reason = manager.entries_allowed()

        # Should be blocked (news checked first)
        assert allowed is False
        assert reason == "negative news pause active"
