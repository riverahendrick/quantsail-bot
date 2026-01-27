"""Integration tests for circuit breakers in trading loop."""

from datetime import datetime, timezone
from unittest.mock import patch

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.config.models import BotConfig


def test_entries_blocked_when_breaker_active(in_memory_db) -> None:
    """Test entries blocked when breaker active."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig()
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    # No breakers active initially
    allowed, _ = manager.entries_allowed()
    assert allowed is True

    # Trigger breaker
    manager.trigger_breaker("volatility", "Test spike", 30, {"atr": 2.0})

    # Entries now blocked
    allowed, reason = manager.entries_allowed()
    assert allowed is False
    assert "volatility" in reason

    # Event emission tested in manager unit tests


def test_breaker_expiry_allows_entries(in_memory_db) -> None:
    """Test entries resume after breaker expires."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig()
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        # Trigger at 12:00
        trigger_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = trigger_time

        manager.trigger_breaker("volatility", "Test", 30, {"atr": 2.0})

        # Check at 12:31 (after expiry)
        later = datetime(2024, 1, 1, 12, 31, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = later

        allowed, _ = manager.entries_allowed()
        assert allowed is True


def test_multiple_breakers_simultaneous(in_memory_db) -> None:
    """Test multiple breakers active simultaneously."""
    from quantsail_engine.persistence.repository import EngineRepository

    config = BotConfig()
    repo = EngineRepository(in_memory_db)
    manager = BreakerManager(config=config.breakers, repo=repo)

    manager.trigger_breaker("volatility", "Vol", 30, {"atr": 2.0})
    manager.trigger_breaker("spread_slippage", "Spread", 60, {"spread_bps": 100.0})
    manager.trigger_breaker("consecutive_losses", "Losses", 180, {"losses": 3})

    assert len(manager.active_breakers) == 3

    allowed, _ = manager.entries_allowed()
    assert allowed is False
