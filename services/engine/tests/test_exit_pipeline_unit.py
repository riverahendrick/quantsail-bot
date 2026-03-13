"""Tests for ExitPipeline — trailing stop, exit detection, and finalization."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest

from quantsail_engine.core.exit_pipeline import ExitPipeline, ExitResult


# --- Helpers ---


def _make_orderbook(mid=50000.0):
    ob = MagicMock()
    ob.mid_price = mid
    return ob


@pytest.fixture
def pipeline():
    """Create an ExitPipeline with all mocked dependencies."""
    cfg = MagicMock()
    cfg.trailing_stop.enabled = True
    cfg.trailing_stop.atr_period = 14

    repo = MagicMock()
    market_data = MagicMock()
    market_data.get_orderbook.return_value = _make_orderbook()
    market_data.get_candles.return_value = [MagicMock(high=50100, low=49900, close=50000)] * 100

    execution_engine = MagicMock()
    trailing_stop_mgr = MagicMock()
    cooldown_gate = MagicMock()
    daily_symbol_limit = MagicMock()
    streak_sizer = MagicMock()

    p = ExitPipeline(
        config=cfg,
        repo=repo,
        market_data_provider=market_data,
        execution_engine=execution_engine,
        trailing_stop_manager=trailing_stop_mgr,
        cooldown_gate=cooldown_gate,
        daily_symbol_limit=daily_symbol_limit,
        streak_sizer=streak_sizer,
    )
    return p


# --- ExitResult ---


def test_exit_result_no_exit():
    """ExitResult with should_exit=False."""
    r = ExitResult(should_exit=False)
    assert not r.should_exit
    assert r.trade is None
    assert r.exit_order is None
    assert r.exit_reason is None


def test_exit_result_with_exit():
    """ExitResult with all fields."""
    r = ExitResult(
        should_exit=True,
        trade={"id": "t1"},
        exit_order={"id": "o1"},
        exit_reason="STOP_LOSS",
    )
    assert r.should_exit
    assert r.trade["id"] == "t1"
    assert r.exit_reason == "STOP_LOSS"


# --- check_trailing_stop ---


@patch("quantsail_engine.core.exit_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_trailing_stop_triggered(mock_atr, pipeline):
    """Trailing stop triggers when price <= new_stop."""
    pipeline.trailing_stop_manager.update.return_value = 49800.0  # Stop level
    pipeline.market_data_provider.get_orderbook.return_value = _make_orderbook(mid=49700.0)  # Below stop

    result = pipeline.check_trailing_stop("BTC/USDT", "trade-1")

    assert result is True
    pipeline.repo.append_event.assert_any_call(
        event_type="trailing_stop.triggered",
        level="INFO",
        payload={
            "symbol": "BTC/USDT",
            "trade_id": "trade-1",
            "stop_level": 49800.0,
            "current_price": 49700.0,
        },
        public_safe=True,
    )


@patch("quantsail_engine.core.exit_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_trailing_stop_not_triggered(mock_atr, pipeline):
    """Trailing stop doesn't trigger when price > stop."""
    pipeline.trailing_stop_manager.update.return_value = 49800.0
    pipeline.market_data_provider.get_orderbook.return_value = _make_orderbook(mid=50200.0)

    result = pipeline.check_trailing_stop("BTC/USDT", "trade-1")
    assert result is False


@patch("quantsail_engine.core.exit_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_trailing_stop_disabled(mock_atr, pipeline):
    """Returns False when trailing stop is disabled in config."""
    pipeline.config.trailing_stop.enabled = False

    result = pipeline.check_trailing_stop("BTC/USDT", "trade-1")
    assert result is False
    pipeline.trailing_stop_manager.update.assert_not_called()


@patch("quantsail_engine.core.exit_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_trailing_stop_no_level_yet(mock_atr, pipeline):
    """Returns False when trailing manager returns None (not activated yet)."""
    pipeline.trailing_stop_manager.update.return_value = None

    result = pipeline.check_trailing_stop("BTC/USDT", "trade-1")
    assert result is False


# --- check_exit ---


def test_check_exit_detected(pipeline):
    """Returns True when execution_engine.check_exits finds an exit."""
    pipeline.execution_engine.check_exits.return_value = {"exit_reason": "STOP_LOSS"}

    result = pipeline.check_exit("BTC/USDT", "trade-1")
    assert result is True


def test_check_exit_none(pipeline):
    """Returns False when no exit detected."""
    pipeline.execution_engine.check_exits.return_value = None

    result = pipeline.check_exit("BTC/USDT", "trade-1")
    assert result is False


# --- finalize_exit ---


def test_finalize_exit_win(pipeline):
    """Winning trade: persists, records win in gates, emits events."""
    trade = {
        "id": "t-win",
        "exit_price": 52000.0,
        "pnl_pct": 4.0,
        "realized_pnl_usd": 20.0,
    }
    exit_order = {"id": "o-win", "order_type": "TAKE_PROFIT"}
    pipeline.execution_engine.check_exits.return_value = {
        "trade": trade,
        "exit_order": exit_order,
        "exit_reason": "TAKE_PROFIT",
    }

    result = pipeline.finalize_exit("BTC/USDT", "t-win")

    assert result.should_exit is True
    assert result.exit_reason == "TAKE_PROFIT"

    # Persistence
    pipeline.repo.update_trade.assert_called_once_with(trade)
    pipeline.repo.save_order.assert_called_once_with(exit_order)

    # Gate recording
    pipeline.cooldown_gate.record_exit.assert_called_once()
    pipeline.daily_symbol_limit.record_win.assert_called_once()
    pipeline.streak_sizer.record_result.assert_called_once_with("BTC/USDT", won=True)

    # Events
    pipeline.repo.append_event.assert_any_call(
        event_type="trade.closed",
        level="INFO",
        payload={
            "trade_id": "t-win",
            "symbol": "BTC/USDT",
            "exit_reason": "TAKE_PROFIT",
            "exit_price": 52000.0,
            "pnl_usd": 20.0,
            "pnl_pct": 4.0,
        },
        public_safe=True,
    )


def test_finalize_exit_loss(pipeline):
    """Losing trade: records loss in gates."""
    trade = {
        "id": "t-loss",
        "exit_price": 49000.0,
        "pnl_pct": -2.0,
        "realized_pnl_usd": -10.0,
    }
    exit_order = {"id": "o-loss", "order_type": "STOP_LOSS"}
    pipeline.execution_engine.check_exits.return_value = {
        "trade": trade,
        "exit_order": exit_order,
        "exit_reason": "STOP_LOSS",
    }

    result = pipeline.finalize_exit("BTC/USDT", "t-loss")

    assert result.should_exit is True
    pipeline.daily_symbol_limit.record_loss.assert_called_once()
    pipeline.streak_sizer.record_result.assert_called_once_with("BTC/USDT", won=False)


def test_finalize_exit_no_exit(pipeline):
    """No exit condition → ExitResult(should_exit=False)."""
    pipeline.execution_engine.check_exits.return_value = None

    result = pipeline.finalize_exit("BTC/USDT", "t-none")

    assert result.should_exit is False
    assert result.trade is None
    pipeline.repo.update_trade.assert_not_called()


def test_finalize_exit_zero_pnl_is_loss(pipeline):
    """Zero PnL is treated as a loss (not a win)."""
    trade = {
        "id": "t-zero",
        "exit_price": 50000.0,
        "pnl_pct": 0.0,
        "realized_pnl_usd": 0.0,
    }
    exit_order = {"id": "o-zero", "order_type": "STOP_LOSS"}
    pipeline.execution_engine.check_exits.return_value = {
        "trade": trade,
        "exit_order": exit_order,
        "exit_reason": "STOP_LOSS",
    }

    pipeline.finalize_exit("BTC/USDT", "t-zero")

    pipeline.daily_symbol_limit.record_loss.assert_called_once()
    pipeline.streak_sizer.record_result.assert_called_once_with("BTC/USDT", won=False)
