"""Tests for the control plane module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.cache.control import (
    BotState,
    InMemoryControlPlane,
    RedisControlPlane,
    get_control_plane,
)


# ---------------------------------------------------------------------------
# BotState enum
# ---------------------------------------------------------------------------


class TestBotState:
    def test_all_states_exist(self) -> None:
        assert BotState.STOPPED.value == "STOPPED"
        assert BotState.ARMED.value == "ARMED"
        assert BotState.RUNNING.value == "RUNNING"
        assert BotState.PAUSED_ENTRIES.value == "PAUSED_ENTRIES"

    def test_from_string(self) -> None:
        assert BotState("RUNNING") == BotState.RUNNING


# ---------------------------------------------------------------------------
# InMemoryControlPlane
# ---------------------------------------------------------------------------


class TestInMemoryControlPlane:
    def test_default_state_is_stopped(self) -> None:
        cp = InMemoryControlPlane()
        assert cp.get_state() == BotState.STOPPED

    def test_initial_state(self) -> None:
        cp = InMemoryControlPlane(BotState.RUNNING)
        assert cp.get_state() == BotState.RUNNING

    def test_set_state(self) -> None:
        cp = InMemoryControlPlane()
        cp.set_state(BotState.ARMED)
        assert cp.get_state() == BotState.ARMED

    def test_entries_allowed_only_running(self) -> None:
        cp = InMemoryControlPlane(BotState.STOPPED)
        assert cp.is_entries_allowed() is False

        cp.set_state(BotState.ARMED)
        assert cp.is_entries_allowed() is False

        cp.set_state(BotState.RUNNING)
        assert cp.is_entries_allowed() is True

        cp.set_state(BotState.PAUSED_ENTRIES)
        assert cp.is_entries_allowed() is False

    def test_exits_allowed_except_stopped(self) -> None:
        cp = InMemoryControlPlane(BotState.STOPPED)
        assert cp.is_exits_allowed() is False

        for state in (BotState.ARMED, BotState.RUNNING, BotState.PAUSED_ENTRIES):
            cp.set_state(state)
            assert cp.is_exits_allowed() is True, f"Exits should be allowed in {state}"

    def test_heartbeat_updates_timestamp(self) -> None:
        cp = InMemoryControlPlane()
        assert cp._last_heartbeat == 0.0
        cp.heartbeat()
        assert cp._last_heartbeat > 0.0


# ---------------------------------------------------------------------------
# RedisControlPlane
# ---------------------------------------------------------------------------


class TestRedisControlPlane:
    def test_get_state_returns_value(self) -> None:
        redis = MagicMock()
        redis.get.return_value = b"RUNNING"
        cp = RedisControlPlane(redis)
        assert cp.get_state() == BotState.RUNNING

    def test_get_state_default_when_none(self) -> None:
        redis = MagicMock()
        redis.get.return_value = None
        cp = RedisControlPlane(redis)
        assert cp.get_state() == BotState.STOPPED

    def test_get_state_default_on_error(self) -> None:
        redis = MagicMock()
        redis.get.side_effect = Exception("Connection refused")
        cp = RedisControlPlane(redis)
        assert cp.get_state() == BotState.STOPPED

    def test_set_state(self) -> None:
        redis = MagicMock()
        cp = RedisControlPlane(redis)
        cp.set_state(BotState.ARMED)
        redis.set.assert_called_once_with("quantsail:control:state", "ARMED")

    def test_set_state_error_raises(self) -> None:
        redis = MagicMock()
        redis.set.side_effect = Exception("Write failed")
        cp = RedisControlPlane(redis)
        with pytest.raises(Exception, match="Write failed"):
            cp.set_state(BotState.RUNNING)

    def test_is_entries_allowed(self) -> None:
        redis = MagicMock()
        redis.get.return_value = b"RUNNING"
        cp = RedisControlPlane(redis)
        assert cp.is_entries_allowed() is True

        redis.get.return_value = b"PAUSED_ENTRIES"
        assert cp.is_entries_allowed() is False

    def test_is_exits_allowed(self) -> None:
        redis = MagicMock()
        redis.get.return_value = b"STOPPED"
        cp = RedisControlPlane(redis)
        assert cp.is_exits_allowed() is False

        redis.get.return_value = b"RUNNING"
        assert cp.is_exits_allowed() is True

    def test_heartbeat(self) -> None:
        redis = MagicMock()
        cp = RedisControlPlane(redis)
        cp.heartbeat()
        redis.set.assert_called_once()
        call_args = redis.set.call_args
        assert call_args[0][0] == "quantsail:control:heartbeat"

    def test_heartbeat_error_does_not_raise(self) -> None:
        redis = MagicMock()
        redis.set.side_effect = Exception("Write error")
        cp = RedisControlPlane(redis)
        # Should not raise
        cp.heartbeat()

    def test_get_state_string_not_bytes(self) -> None:
        """Handle Redis returning string instead of bytes."""
        redis = MagicMock()
        redis.get.return_value = "ARMED"
        cp = RedisControlPlane(redis)
        assert cp.get_state() == BotState.ARMED


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


class TestGetControlPlane:
    def test_returns_in_memory_when_no_url(self) -> None:
        cp = get_control_plane(None)
        assert isinstance(cp, InMemoryControlPlane)

    def test_returns_in_memory_when_empty_url(self) -> None:
        cp = get_control_plane("")
        assert isinstance(cp, InMemoryControlPlane)

    def test_returns_redis_when_url_valid(self) -> None:
        mock_client = MagicMock()
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis.from_url.return_value = mock_client
        with patch.dict("sys.modules", {"redis": mock_redis_mod}):
            cp = get_control_plane("redis://localhost:6379/0")
            assert isinstance(cp, RedisControlPlane)
            mock_client.ping.assert_called_once()

    def test_falls_back_to_inmemory_on_redis_error(self) -> None:
        # Use a bad URL that will cause connection failure
        cp = get_control_plane("redis://nonexistent-host:9999/0")
        assert isinstance(cp, InMemoryControlPlane)
