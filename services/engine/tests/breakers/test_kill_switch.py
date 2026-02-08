"""Tests for emergency kill switch."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

from quantsail_engine.breakers.kill_switch import (
    KillEvent,
    KillReason,
    KillSwitch,
    KillSwitchConfig,
)


class TestKillEvent:
    """Test suite for KillEvent."""

    def test_to_dict(self):
        """Test event serialization."""
        event = KillEvent(
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            reason=KillReason.MANUAL,
            triggered_by="operator",
            details="Manual stop",
        )
        d = event.to_dict()
        assert d["reason"] == "MANUAL"
        assert d["triggered_by"] == "operator"
        assert d["details"] == "Manual stop"
        assert d["acknowledged"] is False

    def test_to_dict_with_auto_resume(self):
        """Test serialization with auto-resume time."""
        resume_time = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        event = KillEvent(
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            reason=KillReason.MAX_DAILY_LOSS,
            triggered_by="auto",
            details="Loss limit",
            auto_resume_at=resume_time,
        )
        d = event.to_dict()
        assert d["auto_resume_at"] == resume_time.isoformat()


class TestKillSwitchConfig:
    """Test suite for KillSwitchConfig."""

    def test_default_values(self):
        """Test default configuration."""
        config = KillSwitchConfig()
        assert config.max_daily_loss_pct == 5.0
        assert config.max_drawdown_pct == 15.0
        assert config.max_consecutive_losses == 5


class TestKillSwitch:
    """Test suite for KillSwitch."""

    @pytest.fixture
    def config(self) -> KillSwitchConfig:
        """Create test config."""
        return KillSwitchConfig(
            max_daily_loss_pct=5.0,
            max_drawdown_pct=15.0,
            max_consecutive_losses=3,
        )

    @pytest.fixture
    def switch(self, config: KillSwitchConfig) -> KillSwitch:
        """Create kill switch with test config."""
        return KillSwitch(config)

    def test_init(self, switch: KillSwitch):
        """Test initialization."""
        assert switch.is_killed is False
        assert switch.current_event is None
        assert switch.history == []

    def test_trigger_manual(self, switch: KillSwitch):
        """Test manual trigger."""
        event = switch.trigger(
            reason=KillReason.MANUAL,
            triggered_by="operator",
            details="Testing",
        )
        
        assert switch.is_killed is True
        assert switch.current_event == event
        assert event.reason == KillReason.MANUAL
        assert len(switch.history) == 1

    def test_trigger_with_auto_resume(self, switch: KillSwitch):
        """Test trigger with auto-resume time."""
        event = switch.trigger(
            reason=KillReason.MANUAL,
            triggered_by="operator",
            details="Short break",
            auto_resume_minutes=30,
        )
        
        assert event.auto_resume_at is not None
        assert event.auto_resume_at > datetime.now(timezone.utc)

    def test_trigger_callback(self, switch: KillSwitch):
        """Test kill callback is called."""
        callback = MagicMock()
        switch.config.on_kill_callbacks.append(callback)
        
        switch.trigger(KillReason.MANUAL, "test", "details")
        
        callback.assert_called_once()

    def test_resume(self, switch: KillSwitch):
        """Test resuming trading."""
        switch.trigger(KillReason.MANUAL, "operator", "Test")
        
        result = switch.resume("operator")
        
        assert result is True
        assert switch.is_killed is False
        assert switch.current_event is None

    def test_resume_not_killed(self, switch: KillSwitch):
        """Test resume when not killed."""
        result = switch.resume("operator")
        assert result is False

    def test_resume_callback(self, switch: KillSwitch):
        """Test resume callback is called."""
        callback = MagicMock()
        switch.config.on_resume_callbacks.append(callback)
        
        switch.trigger(KillReason.MANUAL, "test", "details")
        switch.resume("operator")
        
        callback.assert_called_once()

    def test_check_thresholds_daily_loss(self, switch: KillSwitch):
        """Test daily loss threshold trigger."""
        event = switch.check_thresholds(
            daily_pnl_pct=-6.0,  # Exceeds 5% limit
            current_equity=9400,
            peak_equity=10000,
            consecutive_losses=1,
        )
        
        assert event is not None
        assert event.reason == KillReason.MAX_DAILY_LOSS
        assert switch.is_killed is True

    def test_check_thresholds_drawdown(self, switch: KillSwitch):
        """Test drawdown threshold trigger."""
        event = switch.check_thresholds(
            daily_pnl_pct=-2.0,
            current_equity=8000,  # 20% drawdown from 10000
            peak_equity=10000,
            consecutive_losses=1,
        )
        
        assert event is not None
        assert event.reason == KillReason.MAX_DRAWDOWN
        assert switch.is_killed is True

    def test_check_thresholds_consecutive_losses(self, switch: KillSwitch):
        """Test consecutive losses threshold."""
        event = switch.check_thresholds(
            daily_pnl_pct=-1.0,
            current_equity=9900,
            peak_equity=10000,
            consecutive_losses=3,  # Equals limit
        )
        
        assert event is not None
        assert event.auto_resume_at is not None  # Should have auto-resume

    def test_check_thresholds_no_breach(self, switch: KillSwitch):
        """Test no threshold breach."""
        event = switch.check_thresholds(
            daily_pnl_pct=1.0,
            current_equity=10100,
            peak_equity=10100,
            consecutive_losses=0,
        )
        
        assert event is None
        assert switch.is_killed is False

    def test_check_thresholds_already_killed(self, switch: KillSwitch):
        """Test check when already killed."""
        switch.trigger(KillReason.MANUAL, "test", "test")
        
        event = switch.check_thresholds(
            daily_pnl_pct=-10.0,
            current_equity=8000,
            peak_equity=10000,
            consecutive_losses=10,
        )
        
        assert event is None  # Should not create new event

    def test_check_kill_file_not_exists(self, switch: KillSwitch):
        """Test kill file check when file doesn't exist."""
        switch.config.kill_file_path = "/nonexistent/path"
        
        event = switch.check_kill_file()
        
        assert event is None
        assert switch.is_killed is False

    def test_check_kill_file_exists(self, switch: KillSwitch, tmp_path: Path):
        """Test kill file detection."""
        kill_file = tmp_path / "kill"
        kill_file.write_text("Emergency stop requested")
        switch.config.kill_file_path = str(kill_file)
        
        event = switch.check_kill_file()
        
        assert event is not None
        assert event.reason == KillReason.REMOTE_SIGNAL
        assert "Emergency stop" in event.details

    def test_check_kill_file_disabled(self, switch: KillSwitch, tmp_path: Path):
        """Test kill file check when disabled."""
        kill_file = tmp_path / "kill"
        kill_file.write_text("Stop")
        switch.config.kill_file_path = str(kill_file)
        switch.config.check_kill_file = False
        
        event = switch.check_kill_file()
        
        assert event is None

    def test_get_status(self, switch: KillSwitch):
        """Test status reporting."""
        status = switch.get_status()
        
        assert status["is_killed"] is False
        assert status["current_event"] is None
        assert status["history_count"] == 0

    def test_get_status_when_killed(self, switch: KillSwitch):
        """Test status reporting when killed."""
        switch.trigger(KillReason.MANUAL, "test", "Test kill")
        
        status = switch.get_status()
        
        assert status["is_killed"] is True
        assert status["current_event"] is not None

    def test_to_dict(self, switch: KillSwitch):
        """Test full serialization."""
        switch.trigger(KillReason.MANUAL, "test", "First")
        switch.resume("test")
        switch.trigger(KillReason.MARGIN_CALL, "auto", "Second")
        
        d = switch.to_dict()
        
        assert d["status"]["is_killed"] is True
        assert len(d["history"]) == 2
        assert d["config"]["max_daily_loss_pct"] == 5.0

    def test_history_preserved(self, switch: KillSwitch):
        """Test history is preserved across events."""
        switch.trigger(KillReason.MANUAL, "op1", "First")
        switch.resume("op1")
        switch.trigger(KillReason.EXCHANGE_ERROR, "system", "Second")
        switch.resume("op2")
        
        assert len(switch.history) == 2
        assert switch.history[0].reason == KillReason.MANUAL
        assert switch.history[1].reason == KillReason.EXCHANGE_ERROR

    def test_trigger_callback_exception_does_not_prevent_kill(self, switch: KillSwitch):
        """Test that callback exception doesn't prevent kill switch activation."""
        def failing_callback(event):
            raise Exception("Callback failed")
        
        switch.config.on_kill_callbacks.append(failing_callback)
        
        # Should not raise, and should still kill
        event = switch.trigger(KillReason.MANUAL, "test", "details")
        
        assert switch.is_killed is True
        assert event is not None

    def test_resume_callback_exception_does_not_prevent_resume(self, switch: KillSwitch):
        """Test that callback exception doesn't prevent resume."""
        def failing_callback():
            raise Exception("Resume callback failed")
        
        switch.config.on_resume_callbacks.append(failing_callback)
        switch.trigger(KillReason.MANUAL, "test", "details")
        
        # Should not raise, and should still resume
        result = switch.resume("operator")
        
        assert result is True
        assert switch.is_killed is False

    def test_check_kill_file_already_killed(self, switch: KillSwitch, tmp_path: Path):
        """Test check_kill_file returns None when already killed."""
        kill_file = tmp_path / "kill"
        kill_file.write_text("Stop")
        switch.config.kill_file_path = str(kill_file)
        
        # Kill first
        switch.trigger(KillReason.MANUAL, "test", "already killed")
        
        # Should return None even with file present
        event = switch.check_kill_file()
        
        assert event is None
        assert len(switch.history) == 1  # Only the first trigger

    def test_check_kill_file_read_error(self, switch: KillSwitch, tmp_path: Path):
        """Test check_kill_file handles file read errors gracefully."""
        kill_dir = tmp_path / "kill_dir"
        kill_dir.mkdir()  # Create a directory instead of file
        
        # On Windows/Linux, trying to read a directory as file raises exception
        # Path.exists() returns True for directories, so it will trigger exception path
        switch.config.kill_file_path = str(kill_dir)
        
        # This should still trigger kill due to exception handling (lines 286-291)
        event = switch.check_kill_file()
        
        # It triggers because path exists, but reading fails with exception
        assert event is not None
        assert event.reason == KillReason.REMOTE_SIGNAL
        assert "error reading" in event.details


    @pytest.mark.asyncio
    async def test_start_monitoring_disabled(self, switch: KillSwitch):
        """Test start_monitoring does nothing when disabled."""
        switch.config.check_kill_file = False
        
        await switch.start_monitoring()
        
        assert switch._kill_file_task is None

    @pytest.mark.asyncio
    async def test_start_and_stop_monitoring(self, switch: KillSwitch, tmp_path: Path):
        """Test async monitoring start and stop."""
        import asyncio
        
        kill_file = tmp_path / "kill"
        switch.config.kill_file_path = str(kill_file)
        switch.config.kill_file_check_interval_seconds = 1
        
        await switch.start_monitoring()
        
        assert switch._kill_file_task is not None
        
        # Give it a moment to run
        await asyncio.sleep(0.1)
        
        await switch.stop_monitoring()
        
        assert switch._kill_file_task is None

    @pytest.mark.asyncio
    async def test_stop_monitoring_no_task(self, switch: KillSwitch):
        """Test stop_monitoring when no task is running."""
        # Should not raise
        await switch.stop_monitoring()
        
        assert switch._kill_file_task is None

