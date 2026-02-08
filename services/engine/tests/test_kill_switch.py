"""Tests for the Emergency Kill Switch."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.gates.kill_switch import KillSwitch


@pytest.fixture
def mock_repo() -> MagicMock:
    """Create a mock EngineRepository."""
    return MagicMock()


@pytest.fixture
def kill_switch(mock_repo: MagicMock) -> KillSwitch:
    """Create a KillSwitch instance with mocked repo."""
    return KillSwitch(mock_repo)


class TestKillSwitchInitialization:
    """Tests for KillSwitch initialization."""

    def test_initial_state_is_not_killed(self, kill_switch: KillSwitch) -> None:
        """Kill switch should start in inactive state."""
        assert kill_switch.is_killed is False
        assert kill_switch.reason is None
        assert kill_switch.killed_at is None

    def test_entries_allowed_when_not_killed(self, kill_switch: KillSwitch) -> None:
        """Entries should be allowed when kill switch is inactive."""
        allowed, reason = kill_switch.entries_allowed()
        assert allowed is True
        assert reason is None


class TestKillSwitchTrigger:
    """Tests for triggering the kill switch."""

    def test_trigger_activates_kill_switch(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Triggering should activate the kill switch."""
        result = kill_switch.trigger("Market volatility too high")
        
        assert result["success"] is True
        assert kill_switch.is_killed is True
        assert kill_switch.reason == "Market volatility too high"
        assert kill_switch.killed_at is not None

    def test_trigger_returns_kill_id(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Triggering should return a unique kill_id."""
        result = kill_switch.trigger("Test reason")
        
        assert "kill_id" in result
        assert result["kill_id"].startswith("kill_")

    def test_trigger_emits_emergency_stop_event(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Triggering should emit an emergency.stop event."""
        kill_switch.trigger("System failure", source="auto")
        
        mock_repo.append_event.assert_called_once()
        call_args = mock_repo.append_event.call_args
        assert call_args.kwargs["event_type"] == "emergency.stop"
        assert call_args.kwargs["level"] == "ERROR"
        assert call_args.kwargs["payload"]["reason"] == "System failure"
        assert call_args.kwargs["payload"]["source"] == "auto"
        assert call_args.kwargs["public_safe"] is False

    def test_trigger_includes_action_flags(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Triggering should include cancel_pending and close_positions flags."""
        result = kill_switch.trigger(
            "Emergency", cancel_pending=True, close_positions=True
        )
        
        assert result["actions"]["cancel_pending"] is True
        assert result["actions"]["close_positions"] is True

    def test_trigger_when_already_killed_returns_failure(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Triggering when already killed should return failure."""
        kill_switch.trigger("First trigger")
        result = kill_switch.trigger("Second trigger")
        
        assert result["success"] is False
        assert result["message"] == "Kill switch already active"
        # Only one event should have been emitted
        assert mock_repo.append_event.call_count == 1

    def test_entries_blocked_after_trigger(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Entries should be blocked after kill switch is triggered."""
        kill_switch.trigger("Test block")
        
        allowed, reason = kill_switch.entries_allowed()
        assert allowed is False
        assert "Emergency stop active" in reason
        assert "Test block" in reason


class TestKillSwitchReset:
    """Tests for resetting the kill switch."""

    def test_reset_without_confirmation_fails(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Reset without confirmation should fail."""
        kill_switch.trigger("Test")
        result = kill_switch.reset(confirm=False)
        
        assert result["success"] is False
        assert "Must confirm" in result["message"]
        assert kill_switch.is_killed is True

    def test_reset_when_not_killed_fails(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Reset when not killed should fail."""
        result = kill_switch.reset(confirm=True)
        
        assert result["success"] is False
        assert "not active" in result["message"]

    def test_reset_with_confirmation_succeeds(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Reset with confirmation should succeed."""
        kill_switch.trigger("Test trigger")
        result = kill_switch.reset(confirm=True)
        
        assert result["success"] is True
        assert kill_switch.is_killed is False
        assert kill_switch.reason is None
        assert kill_switch.killed_at is None

    def test_reset_emits_emergency_reset_event(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Reset should emit an emergency.reset event."""
        kill_switch.trigger("Test trigger")
        mock_repo.reset_mock()
        
        kill_switch.reset(confirm=True, source="api")
        
        mock_repo.append_event.assert_called_once()
        call_args = mock_repo.append_event.call_args
        assert call_args.kwargs["event_type"] == "emergency.reset"
        assert call_args.kwargs["level"] == "WARN"
        assert call_args.kwargs["payload"]["source"] == "api"

    def test_reset_returns_previous_kill_info(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Reset should return previous kill information."""
        kill_switch.trigger("Original reason")
        result = kill_switch.reset(confirm=True)
        
        assert result["previous_reason"] == "Original reason"
        assert result["previous_kill_id"] is not None

    def test_entries_allowed_after_reset(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Entries should be allowed after reset."""
        kill_switch.trigger("Test")
        kill_switch.reset(confirm=True)
        
        allowed, reason = kill_switch.entries_allowed()
        assert allowed is True
        assert reason is None


class TestKillSwitchStatus:
    """Tests for kill switch status."""

    def test_status_when_inactive(self, kill_switch: KillSwitch) -> None:
        """Status should show inactive when not killed."""
        status = kill_switch.get_status()
        
        assert status["active"] is False
        assert status["kill_id"] is None
        assert status["reason"] is None
        assert status["killed_at"] is None

    def test_status_when_active(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Status should show active with details when killed."""
        kill_switch.trigger("Status test reason")
        status = kill_switch.get_status()
        
        assert status["active"] is True
        assert status["reason"] == "Status test reason"
        assert status["kill_id"] is not None
        assert status["killed_at"] is not None


class TestKillSwitchMultipleCycles:
    """Tests for multiple trigger/reset cycles."""

    def test_can_trigger_after_reset(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Should be able to trigger again after reset."""
        kill_switch.trigger("First")
        kill_switch.reset(confirm=True)
        result = kill_switch.trigger("Second")
        
        assert result["success"] is True
        assert kill_switch.reason == "Second"

    def test_different_kill_ids_each_cycle(
        self, kill_switch: KillSwitch, mock_repo: MagicMock
    ) -> None:
        """Each trigger should get a unique kill_id."""
        with patch("quantsail_engine.gates.kill_switch.datetime") as mock_dt:
            # First trigger at time T1
            mock_dt.now.return_value = datetime(2026, 2, 5, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.timezone = timezone
            result1 = kill_switch.trigger("First")
            kill_id1 = result1["kill_id"]
            
            kill_switch.reset(confirm=True)
            
            # Second trigger at time T2
            mock_dt.now.return_value = datetime(2026, 2, 5, 10, 0, 1, tzinfo=timezone.utc)
            result2 = kill_switch.trigger("Second")
            kill_id2 = result2["kill_id"]
        
        assert kill_id1 != kill_id2
