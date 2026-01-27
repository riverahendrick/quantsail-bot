"""Unit tests for circuit breaker manager."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.config.models import BreakerConfig


@pytest.fixture
def mock_repo():
    """Create mock repository."""
    repo = MagicMock()
    repo.append_event = MagicMock()
    return repo


@pytest.fixture
def breaker_config():
    """Create default breaker config."""
    return BreakerConfig()


@pytest.fixture
def manager(breaker_config, mock_repo):
    """Create breaker manager with default config."""
    return BreakerManager(config=breaker_config, repo=mock_repo)


def test_entries_allowed_no_breakers(manager) -> None:
    """Test entries allowed when no breakers active."""
    allowed, reason = manager.entries_allowed()

    assert allowed is True
    assert reason is None


def test_entries_allowed_breaker_active(manager, mock_repo) -> None:
    """Test entries blocked when breaker active."""
    manager.trigger_breaker(
        "volatility",
        "ATR spike detected",
        30,
        {"atr": 2.0, "candle_range": 7.0}
    )

    allowed, reason = manager.entries_allowed()

    assert allowed is False
    assert reason is not None
    assert "volatility" in reason
    assert "ATR spike detected" in reason


def test_exits_allowed_always_true(manager, mock_repo) -> None:
    """Test exits always allowed even with active breakers."""
    # Trigger breaker
    manager.trigger_breaker(
        "volatility",
        "ATR spike detected",
        30,
        {"atr": 2.0}
    )

    allowed, reason = manager.exits_allowed()

    assert allowed is True
    assert reason is None


def test_trigger_breaker_creates_active_breaker(manager, mock_repo) -> None:
    """Test triggering breaker creates active breaker."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        manager.trigger_breaker(
            "spread_slippage",
            "Spread spike",
            60,
            {"spread_bps": 100.0}
        )

        assert "spread_slippage" in manager.active_breakers
        breaker = manager.active_breakers["spread_slippage"]
        assert breaker.breaker_type == "spread_slippage"
        assert breaker.reason == "Spread spike"
        assert breaker.triggered_at == now
        assert breaker.expires_at == now + timedelta(minutes=60)
        assert breaker.context == {"spread_bps": 100.0}


def test_trigger_breaker_emits_event(manager, mock_repo) -> None:
    """Test triggering breaker emits breaker.triggered event."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        manager.trigger_breaker(
            "consecutive_losses",
            "Too many losses",
            180,
            {"consecutive_losses": 3, "losing_trade_ids": ["t1", "t2", "t3"]}
        )

        mock_repo.append_event.assert_called_once()
        call_args = mock_repo.append_event.call_args
        assert call_args[1]["event_type"] == "breaker.triggered"
        assert call_args[1]["level"] == "WARN"
        assert call_args[1]["public_safe"] is True
        payload = call_args[1]["payload"]
        assert payload["breaker_type"] == "consecutive_losses"
        assert payload["reason"] == "Too many losses"
        assert payload["pause_minutes"] == 180
        assert payload["consecutive_losses"] == 3


def test_expire_breakers_removes_expired(manager, mock_repo) -> None:
    """Test breaker expiry removes expired breakers."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        # Trigger at 12:00
        trigger_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = trigger_time

        manager.trigger_breaker("volatility", "Test", 30, {"atr": 2.0})
        mock_repo.append_event.reset_mock()

        # Check at 12:31 (after expiry)
        check_time = datetime(2024, 1, 1, 12, 31, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = check_time

        allowed, _ = manager.entries_allowed()

        assert allowed is True
        assert "volatility" not in manager.active_breakers


def test_expire_breakers_emits_event(manager, mock_repo) -> None:
    """Test breaker expiry emits breaker.expired event."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        # Trigger at 12:00
        trigger_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = trigger_time

        manager.trigger_breaker("spread_slippage", "Test", 60, {"spread_bps": 100.0})
        mock_repo.append_event.reset_mock()

        # Check at 13:05 (65 minutes later)
        check_time = datetime(2024, 1, 1, 13, 5, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = check_time

        manager.entries_allowed()

        mock_repo.append_event.assert_called_once()
        call_args = mock_repo.append_event.call_args
        assert call_args[1]["event_type"] == "breaker.expired"
        assert call_args[1]["level"] == "INFO"
        assert call_args[1]["public_safe"] is True
        payload = call_args[1]["payload"]
        assert payload["breaker_type"] == "spread_slippage"
        assert payload["was_active_for_minutes"] == 65.0


def test_multiple_breakers_simultaneous(manager, mock_repo) -> None:
    """Test multiple breakers can be active simultaneously."""
    manager.trigger_breaker("volatility", "Vol spike", 30, {"atr": 2.0})
    manager.trigger_breaker("spread_slippage", "Spread spike", 60, {"spread_bps": 100.0})
    manager.trigger_breaker("consecutive_losses", "Losses", 180, {"losses": 3})

    assert len(manager.active_breakers) == 3
    assert "volatility" in manager.active_breakers
    assert "spread_slippage" in manager.active_breakers
    assert "consecutive_losses" in manager.active_breakers

    allowed, reason = manager.entries_allowed()
    assert allowed is False
    assert reason is not None


def test_breaker_not_expired_yet(manager, mock_repo) -> None:
    """Test breaker remains active before expiry."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        # Trigger at 12:00
        trigger_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = trigger_time

        manager.trigger_breaker("volatility", "Test", 30, {"atr": 2.0})

        # Check at 12:15 (before expiry)
        check_time = datetime(2024, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = check_time

        allowed, _ = manager.entries_allowed()

        assert allowed is False
        assert "volatility" in manager.active_breakers


def test_partial_expiry_multiple_breakers(manager, mock_repo) -> None:
    """Test some breakers expire while others remain active."""
    with patch("quantsail_engine.breakers.manager.datetime") as mock_dt:
        # Trigger both at 12:00
        trigger_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = trigger_time

        manager.trigger_breaker("volatility", "Vol", 30, {"atr": 2.0})
        manager.trigger_breaker("spread_slippage", "Spread", 120, {"spread_bps": 100.0})

        # Check at 12:45 (volatility expired, spread still active)
        check_time = datetime(2024, 1, 1, 12, 45, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = check_time

        allowed, reason = manager.entries_allowed()

        assert allowed is False  # Still blocked by spread_slippage
        assert "volatility" not in manager.active_breakers
        assert "spread_slippage" in manager.active_breakers
        assert "spread_slippage" in reason
