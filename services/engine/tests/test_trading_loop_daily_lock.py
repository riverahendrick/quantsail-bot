"""Integration tests for TradingLoop daily lock."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock


from quantsail_engine.config.models import BotConfig, DailyConfig, ExecutionConfig
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.models.signal import SignalType
from quantsail_engine.persistence.stub_models import Event, Trade
from quantsail_engine.signals.stub_provider import StubSignalProvider


def test_daily_lock_blocks_entry(in_memory_db) -> None:
    """Test that daily lock blocks new entries when target reached."""
    # Setup: Daily Lock STOP mode, Target $50
    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        daily=DailyConfig(
            enabled=True,
            mode="STOP",
            target_usd=50.0,
            timezone="UTC"
        )
    )
    
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    signals.set_next_signal(SignalType.ENTER_LONG)
    executor = DryRunExecutor()

    # Pre-seed DB with a closed trade that hits target
    now = datetime.now(timezone.utc)
    t_id = uuid.uuid4()
    trade = Trade(
        id=t_id, symbol="BTC/USDT", mode="dry-run", status="CLOSED",
        side="BUY", entry_price=100, entry_qty=1, opened_at=now, closed_at=now,
        realized_pnl_usd=50.0 # Hits target exactly
    )
    in_memory_db.add(trade)
    in_memory_db.commit()
    
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()
    
    # Verify no new trade opened
    # We should have 1 trade in DB (the pre-seeded one)
    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].id == t_id
    
    # Verify event emitted
    events = in_memory_db.query(Event).all()
    event_types = [e.type for e in events]
    
    assert "daily_lock.engaged" in event_types
    assert "gate.daily_lock.rejected" in event_types

def test_daily_lock_overdrive_floor_breach(in_memory_db) -> None:
    """Test OVERDRIVE mode blocks entries when floor breached."""
    # Setup: Overdrive, Target 50, Buffer 10
    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        daily=DailyConfig(
            enabled=True,
            mode="OVERDRIVE",
            target_usd=50.0,
            overdrive_trailing_buffer_usd=10.0,
            timezone="UTC"
        )
    )

    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    signals.set_next_signal(SignalType.ENTER_LONG)
    executor = DryRunExecutor()

    # Pre-seed DB:
    # 1. Hit 60 (Peak) -> Floor 50
    # 2. Lose 15 -> Current 45 (Below Floor)
    now = datetime.now(timezone.utc)
    t1 = Trade(
        id=uuid.uuid4(), symbol="BTC/USDT", mode="dry-run", status="CLOSED", side="BUY",
        entry_price=100, entry_qty=1, opened_at=now, closed_at=now,
        realized_pnl_usd=60.0
    )
    t2 = Trade(
        id=uuid.uuid4(), symbol="BTC/USDT", mode="dry-run", status="CLOSED", side="BUY",
        entry_price=100, entry_qty=1, opened_at=now, closed_at=now,
        realized_pnl_usd=-15.0
    )
    # Net: +45. Peak: 60. Floor: 50. Current < Floor -> Locked.
    
    in_memory_db.add_all([t1, t2])
    in_memory_db.commit()
    
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()
    
    # No new trade
    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 2
    
    events = in_memory_db.query(Event).all()
    event_types = [e.type for e in events]
    
    # daily_lock.engaged is NOT emitted because state was reconstructed silently
    assert "daily_lock.entries_paused" in event_types
    assert "gate.daily_lock.rejected" in event_types
