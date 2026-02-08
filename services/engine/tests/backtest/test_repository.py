"""Tests for BacktestRepository."""

import pytest
from datetime import datetime, timezone, timedelta

from quantsail_engine.backtest.repository import BacktestRepository
from quantsail_engine.backtest.time_manager import TimeManager


class TestBacktestRepositoryInit:
    """Test repository initialization."""

    def test_init_in_memory(self):
        """Test in-memory database initialization."""
        repo = BacktestRepository(":memory:")
        assert repo.db_path == ":memory:"
        assert repo._circuit_breaker_triggers == 0
        assert repo._daily_lock_hits == 0
        repo.close()

    def test_init_with_time_manager(self):
        """Test initialization with TimeManager."""
        tm = TimeManager()
        repo = BacktestRepository(":memory:", time_manager=tm)
        assert repo.time_manager is tm
        repo.close()


class TestBacktestRepositoryNow:
    """Test _now() method."""

    def test_now_without_time_manager(self):
        """Test _now returns real time when no time manager."""
        repo = BacktestRepository(":memory:")
        now = repo._now()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc
        repo.close()

    def test_now_with_time_manager_set(self):
        """Test _now returns simulated time."""
        tm = TimeManager()
        simulated = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        tm.set_time(simulated)
        
        repo = BacktestRepository(":memory:", time_manager=tm)
        now = repo._now()
        
        assert now == simulated
        repo.close()

    def test_now_with_time_manager_not_set(self):
        """Test _now falls back to real time when time not set."""
        tm = TimeManager()  # Not calling set_time
        repo = BacktestRepository(":memory:", time_manager=tm)
        
        # Should not raise, should return real time
        now = repo._now()
        assert isinstance(now, datetime)
        repo.close()


class TestBacktestRepositoryAppendEvent:
    """Test append_event method."""

    def test_append_event_basic(self):
        """Test basic event appending."""
        repo = BacktestRepository(":memory:")
        
        seq = repo.append_event(
            event_type="test.event",
            level="INFO",
            payload={"key": "value"},
            public_safe=True,
        )
        
        assert seq >= 0
        events = repo.get_events("test.event")
        assert len(events) >= 1
        event = next(e for e in events if e["type"] == "test.event")
        assert event["type"] == "test.event"
        repo.close()

    def test_append_event_circuit_breaker(self):
        """Test circuit breaker event is tracked."""
        repo = BacktestRepository(":memory:")
        
        repo.append_event(
            event_type="breaker.triggered",
            level="WARN",
            payload={"breaker": "max_position"},
        )
        
        assert repo.get_circuit_breaker_count() == 1
        repo.close()

    def test_append_event_daily_lock_engaged(self):
        """Test daily lock engaged event is tracked."""
        repo = BacktestRepository(":memory:")
        
        repo.append_event(
            event_type="daily_lock.engaged",
            level="WARN",
            payload={},
        )
        
        assert repo.get_daily_lock_count() == 1
        repo.close()

    def test_append_event_daily_lock_paused(self):
        """Test daily lock entries paused event is tracked."""
        repo = BacktestRepository(":memory:")
        
        repo.append_event(
            event_type="daily_lock.entries_paused",
            level="WARN",
            payload={},
        )
        
        assert repo.get_daily_lock_count() == 1
        repo.close()

    def test_append_event_with_decimal_payload(self):
        """Test event with Decimal in payload is serialized."""
        from decimal import Decimal
        repo = BacktestRepository(":memory:")
        
        seq = repo.append_event(
            event_type="test.decimal.value",
            level="INFO",
            payload={"price": Decimal("123.456")},
        )
        
        assert seq >= 0
        repo.close()

    def test_append_event_with_datetime_payload(self):
        """Test event with datetime in payload is serialized."""
        repo = BacktestRepository(":memory:")
        
        seq = repo.append_event(
            event_type="test.datetime.value",
            level="INFO",
            payload={"timestamp": datetime.now(timezone.utc)},
        )
        
        assert seq >= 0
        repo.close()


class TestBacktestRepositoryEquity:
    """Test equity-related methods."""

    def test_save_equity_snapshot(self):
        """Test saving an equity snapshot."""
        repo = BacktestRepository(":memory:")
        
        repo.save_equity_snapshot(
            equity_usd=10500.0,
            cash_usd=5000.0,
            unrealized_pnl_usd=500.0,
        )
        
        curve = repo.get_equity_curve()
        assert len(curve) == 1
        assert curve[0][1] == 10500.0
        repo.close()

    def test_get_equity_curve_empty(self):
        """Test get_equity_curve with no snapshots."""
        repo = BacktestRepository(":memory:")
        
        curve = repo.get_equity_curve()
        assert curve == []
        repo.close()

    def test_calculate_equity(self):
        """Test calculate_equity sums closed trades."""
        from quantsail_engine.persistence.stub_models import Trade
        import uuid
        
        repo = BacktestRepository(":memory:")
        
        # Create a closed trade with PnL
        trade = Trade(
            id=uuid.uuid4(),
            symbol="BTC/USDT",
            mode="BACKTEST",
            status="CLOSED",
            side="LONG",
            entry_price=50000.0,
            entry_qty=0.1,
            entry_notional_usd=5000.0,
            realized_pnl_usd=250.0,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )
        repo.session.add(trade)
        repo.session.commit()
        
        equity = repo.calculate_equity(10000.0)
        assert equity == 10250.0
        repo.close()


class TestBacktestRepositoryTodayMethods:
    """Test today-related methods with TimeManager."""

    def test_get_today_realized_pnl_with_time_manager(self):
        """Test get_today_realized_pnl uses time manager."""
        from quantsail_engine.persistence.stub_models import Trade
        import uuid
        
        tm = TimeManager()
        simulated = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        tm.set_time(simulated)
        
        repo = BacktestRepository(":memory:", time_manager=tm)
        
        # Create a trade closed "today" in simulated time
        trade = Trade(
            id=uuid.uuid4(),
            symbol="ETH/USDT",
            mode="BACKTEST",
            status="CLOSED",
            side="LONG",
            entry_price=3000.0,
            entry_qty=1.0,
            entry_notional_usd=3000.0,
            realized_pnl_usd=100.0,
            opened_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        repo.session.add(trade)
        repo.session.commit()
        
        pnl = repo.get_today_realized_pnl()
        assert pnl == 100.0
        repo.close()

    def test_get_today_realized_pnl_without_time_manager(self):
        """Test get_today_realized_pnl without time manager."""
        repo = BacktestRepository(":memory:")
        pnl = repo.get_today_realized_pnl()
        assert pnl == 0.0
        repo.close()

    def test_get_today_closed_trades_with_time_manager(self):
        """Test get_today_closed_trades uses time manager."""
        from quantsail_engine.persistence.stub_models import Trade
        import uuid
        
        tm = TimeManager()
        simulated = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        tm.set_time(simulated)
        
        repo = BacktestRepository(":memory:", time_manager=tm)
        
        # Trade from "today"
        trade = Trade(
            id=uuid.uuid4(),
            symbol="BTC/USDT",
            mode="BACKTEST",
            status="CLOSED",
            side="LONG",
            entry_price=50000.0,
            entry_qty=0.01,
            entry_notional_usd=500.0,
            realized_pnl_usd=50.0,
            opened_at=datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        repo.session.add(trade)
        repo.session.commit()
        
        trades = repo.get_today_closed_trades()
        assert len(trades) == 1
        repo.close()

    def test_get_today_closed_trades_without_time_manager(self):
        """Test get_today_closed_trades without time manager."""
        repo = BacktestRepository(":memory:")
        trades = repo.get_today_closed_trades()
        assert trades == []
        repo.close()


class TestBacktestRepositoryEvents:
    """Test event query methods."""

    def test_get_events_all(self):
        """Test get_events returns all events."""
        repo = BacktestRepository(":memory:")
        
        repo.append_event("event.a", "INFO", {})
        repo.append_event("event.b", "WARN", {})
        
        events = repo.get_events()
        assert len(events) == 2
        repo.close()

    def test_get_events_filtered(self):
        """Test get_events filters by type."""
        repo = BacktestRepository(":memory:")
        
        repo.append_event("event.a", "INFO", {})
        repo.append_event("event.b", "WARN", {})
        repo.append_event("event.a", "INFO", {})
        
        events = repo.get_events("event.a")
        assert len(events) == 2
        repo.close()


class TestBacktestRepositoryTrades:
    """Test trade-related methods."""

    def test_get_all_trades_empty(self):
        """Test get_all_trades with no trades."""
        repo = BacktestRepository(":memory:")
        trades = repo.get_all_trades()
        assert trades == []
        repo.close()

    def test_get_all_trades_returns_dicts(self):
        """Test get_all_trades returns proper dict format."""
        from quantsail_engine.persistence.stub_models import Trade
        import uuid
        
        repo = BacktestRepository(":memory:")
        trade_id = uuid.uuid4()
        
        trade = Trade(
            id=trade_id,
            symbol="ETH/USDT",
            mode="BACKTEST",
            status="OPEN",
            side="LONG",
            entry_price=3000.0,
            entry_qty=1.0,
            entry_notional_usd=3000.0,
            opened_at=datetime.now(timezone.utc),
        )
        repo.session.add(trade)
        repo.session.commit()
        
        trades = repo.get_all_trades()
        assert len(trades) == 1
        assert trades[0]["id"] == str(trade_id)
        assert trades[0]["symbol"] == "ETH/USDT"
        assert "entry_price" in trades[0]
        repo.close()
