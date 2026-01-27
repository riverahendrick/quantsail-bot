"""Tests for DailyLockManager."""

from unittest.mock import MagicMock

import pytest

from quantsail_engine.config.models import DailyConfig
from quantsail_engine.gates.daily_lock import DailyLockManager


class MockRepo:
    def __init__(self):
        self.pnl = 0.0
        self.closed_trades = []
        self.events = []

    def get_today_realized_pnl(self, timezone_str="UTC"):
        return self.pnl

    def get_today_closed_trades(self, timezone_str="UTC"):
        return self.closed_trades
    
    def append_event(self, event_type, level, payload, public_safe=False):
        self.events.append((event_type, payload))

@pytest.fixture
def repo():
    return MockRepo()

def test_disabled(repo):
    config = DailyConfig(enabled=False, mode="STOP", target_usd=100.0)
    manager = DailyLockManager(config, repo)
    repo.pnl = 200.0
    allowed, _ = manager.entries_allowed()
    assert allowed is True

def test_stop_mode_below_target(repo):
    config = DailyConfig(enabled=True, mode="STOP", target_usd=100.0)
    manager = DailyLockManager(config, repo)
    
    repo.pnl = 50.0
    allowed, reason = manager.entries_allowed()
    assert allowed is True
    assert reason is None

def test_stop_mode_hit_target(repo):
    config = DailyConfig(enabled=True, mode="STOP", target_usd=100.0)
    manager = DailyLockManager(config, repo)
    
    repo.pnl = 100.0
    allowed, reason = manager.entries_allowed()
    assert allowed is False
    assert reason is not None
    assert "Daily target reached" in reason
    
    # Check event
    assert len(repo.events) > 0
    assert repo.events[0][0] == "daily_lock.engaged"
    assert repo.events[0][1]["realized_pnl"] == 100.0

def test_overdrive_mode_climbing(repo):
    config = DailyConfig(
        enabled=True, 
        mode="OVERDRIVE", 
        target_usd=100.0,
        overdrive_trailing_buffer_usd=10.0
    )
    manager = DailyLockManager(config, repo)
    
    # Hit target, peak = 100, floor = 90
    repo.pnl = 100.0
    allowed, _ = manager.entries_allowed()
    assert allowed is True
    assert manager.peak_realized_pnl == 100.0
    
    # Climb to 120, peak = 120, floor = 110
    repo.pnl = 120.0
    allowed, _ = manager.entries_allowed()
    assert allowed is True
    assert manager.peak_realized_pnl == 120.0
    
    # Check events
    event_types = [e[0] for e in repo.events]
    assert "daily_lock.engaged" in event_types
    assert "daily_lock.floor_updated" in event_types

def test_overdrive_mode_drawdown_pause(repo):
    config = DailyConfig(
        enabled=True, 
        mode="OVERDRIVE", 
        target_usd=100.0,
        overdrive_trailing_buffer_usd=10.0
    )
    manager = DailyLockManager(config, repo)
    
    # Peak 120, Floor 110
    repo.pnl = 120.0
    manager.entries_allowed()
    
    # Drawdown to 115 (above floor)
    repo.pnl = 115.0
    allowed, _ = manager.entries_allowed()
    assert allowed is True
    
    # Drawdown to 109 (below floor)
    repo.pnl = 109.0
    allowed, reason = manager.entries_allowed()
    assert allowed is False
    assert "profit floor breached" in reason
    
    event_types = [e[0] for e in repo.events]
    assert "daily_lock.entries_paused" in event_types

def test_reconstruct_peak_from_trades(repo):
    config = DailyConfig(
        enabled=True, 
        mode="OVERDRIVE", 
        target_usd=100.0,
        overdrive_trailing_buffer_usd=10.0
    )
    
    # Mock closed trades
    t1 = MagicMock()
    t1.pnl_usd = 50.0
    t2 = MagicMock()
    t2.pnl_usd = 80.0 # Cumulative 130
    t3 = MagicMock()
    t3.pnl_usd = -20.0 # Cumulative 110
    
    repo.closed_trades = [t1, t2, t3]
    repo.pnl = 110.0
    
    manager = DailyLockManager(config, repo)
    # Peak should be 130.0 from trade history
    
    # First check calls _update_state which calls _reconstruct_peak_if_needed
    manager.entries_allowed()
    
    assert manager.peak_realized_pnl == 130.0
    assert manager.floor_usd == 120.0 # 130 - 10
    
    # Current PnL is 110, which is below floor 120 -> Paused
    allowed, _ = manager.entries_allowed()
    assert allowed is False
