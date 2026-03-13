"""Tests for EntryPipeline — each gate is tested in isolation via mocks."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest

from quantsail_engine.core.entry_pipeline import EntryPipeline
from quantsail_engine.models.signal import Signal, SignalType
from quantsail_engine.models.strategy import StrategyOutput


# --- Helpers ---


def _make_config():
    """Return a minimal mock BotConfig for the entry pipeline."""
    cfg = MagicMock()
    cfg.symbols.max_concurrent_positions = 5
    cfg.execution.taker_fee_bps = 10
    cfg.risk.starting_cash_usd = 10000.0
    cfg.stop_loss.method = "atr"
    cfg.stop_loss.atr_multiplier = 2.0
    cfg.stop_loss.fixed_pct = 2.0
    cfg.take_profit.method = "risk_reward"
    cfg.take_profit.risk_reward_ratio = 2.0
    cfg.take_profit.atr_multiplier = 3.0
    cfg.take_profit.fixed_pct = 4.0
    cfg.breakers.volatility = MagicMock()
    cfg.breakers.volatility.pause_minutes = 30
    cfg.breakers.spread_slippage = MagicMock()
    cfg.breakers.spread_slippage.pause_minutes = 15
    cfg.breakers.consecutive_losses = MagicMock()
    cfg.breakers.consecutive_losses.pause_minutes = 60
    return cfg


def _make_orderbook(mid=50000.0, best_ask=50010.0, best_bid=49990.0):
    """Return a mock orderbook."""
    ob = MagicMock()
    ob.mid_price = mid
    ob.best_ask = best_ask
    ob.best_bid = best_bid
    ob.asks = [(best_ask, 1.0)]
    ob.bids = [(best_bid, 1.0)]
    return ob


def _make_candles(n=100):
    """Return a list of mock candles for ATR calculation."""
    return [MagicMock(high=50100 + i, low=49900 + i, close=50000 + i) for i in range(n)]


def _make_long_signal(confidence=0.8):
    """Return a Signal indicating ENTER_LONG."""
    return Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=confidence,
        strategy_outputs=[
            StrategyOutput(strategy_name="trend", signal=SignalType.ENTER_LONG, confidence=0.9, rationale={"reason": "EMA cross"}),
        ],
    )


def _make_hold_signal():
    """Return a HOLD signal."""
    return Signal(
        signal_type=SignalType.HOLD,
        symbol="BTC/USDT",
        confidence=0.3,
        strategy_outputs=[
            StrategyOutput(strategy_name="trend", signal=SignalType.HOLD, confidence=0.3, rationale={"reason": "No signal"}),
        ],
    )


@pytest.fixture
def pipeline():
    """Create an EntryPipeline with all mocked dependencies."""
    cfg = _make_config()
    repo = MagicMock()
    repo.calculate_equity.return_value = 10000.0

    market_data = MagicMock()
    market_data.get_candles.return_value = _make_candles()
    market_data.get_orderbook.return_value = _make_orderbook()

    signal_provider = MagicMock()
    signal_provider.generate_signal.return_value = _make_long_signal()

    breaker_manager = MagicMock()
    breaker_manager.entries_allowed.return_value = (True, None)

    daily_lock = MagicMock()
    daily_lock.entries_allowed.return_value = (True, None)

    dynamic_sizer = MagicMock()
    dynamic_sizer.calculate.return_value = 0.01

    regime_filter = MagicMock()
    regime_filter.analyze.return_value = True

    profitability_gate = MagicMock()
    profitability_gate.evaluate.return_value = (True, {"net_profit_usd": 5.0})

    cooldown_gate = MagicMock()
    cooldown_gate.is_allowed.return_value = (True, None)

    daily_symbol_limit = MagicMock()
    daily_symbol_limit.is_allowed.return_value = (True, None)

    streak_sizer = MagicMock()
    streak_sizer.get_multiplier.return_value = 1.0

    p = EntryPipeline(
        config=cfg,
        repo=repo,
        market_data_provider=market_data,
        signal_provider=signal_provider,
        breaker_manager=breaker_manager,
        daily_lock_manager=daily_lock,
        dynamic_sizer=dynamic_sizer,
        regime_filter=regime_filter,
        profitability_gate=profitability_gate,
        cooldown_gate=cooldown_gate,
        daily_symbol_limit=daily_symbol_limit,
        streak_sizer=streak_sizer,
    )
    return p


# --- Happy path ---


@patch("quantsail_engine.core.entry_pipeline.check_volatility_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_spread_slippage_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_consecutive_losses", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.calculate_slippage", return_value=(50005.0, 0.5))
@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_evaluate_happy_path(mock_atr, mock_slip, mock_cl, mock_ss, mock_vs, pipeline):
    """All gates pass → returns a TradePlan."""
    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)

    assert result is not None
    assert result.symbol == "BTC/USDT"
    assert result.side == "BUY"
    assert result.stop_loss_price > 0
    assert result.take_profit_price > result.entry_price


# --- Gate: Regime filter rejects ---


def test_regime_filter_rejects(pipeline):
    """Regime filter rejection → None."""
    pipeline.regime_filter.analyze.return_value = False

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)

    assert result is None
    pipeline.repo.append_event.assert_any_call(
        event_type="gate.regime.rejected",
        level="INFO",
        payload={"symbol": "BTC/USDT", "reason": "choppy_market_detected"},
        public_safe=True,
    )


# --- Gate: Cooldown rejects ---


def test_cooldown_gate_rejects(pipeline):
    """Cooldown gate → None."""
    pipeline.regime_filter.analyze.return_value = True
    pipeline.cooldown_gate.is_allowed.return_value = (False, "cooldown_active")

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)
    assert result is None


# --- Gate: Daily symbol limit rejects ---


def test_daily_symbol_limit_rejects(pipeline):
    """Daily symbol limit → None."""
    pipeline.daily_symbol_limit.is_allowed.return_value = (False, "limit_reached")

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)
    assert result is None


# --- Gate: Signal is HOLD ---


def test_hold_signal_returns_none(pipeline):
    """HOLD signal → no trade."""
    pipeline.signal_provider.generate_signal.return_value = _make_hold_signal()

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)
    assert result is None


# --- Gate: Breaker rejects ---


@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0])
def test_breaker_rejects(mock_atr, pipeline):
    """Breaker rejection → None."""
    pipeline.breaker_manager.entries_allowed.return_value = (False, "news_pause_active")

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)

    assert result is None
    pipeline.repo.append_event.assert_any_call(
        event_type="gate.news.rejected",
        level="WARN",
        payload={"symbol": "BTC/USDT", "reason": "news_pause_active"},
        public_safe=True,
    )


# --- Gate: Daily lock rejects ---


@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0])
def test_daily_lock_rejects(mock_atr, pipeline):
    """Daily lock → None."""
    pipeline.daily_lock_manager.entries_allowed.return_value = (False, "daily_target_reached")

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)
    assert result is None


# --- Gate: Max positions ---


@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0])
def test_max_positions_rejects(mock_atr, pipeline):
    """Max concurrent positions → None."""
    pipeline.config.symbols.max_concurrent_positions = 3

    result = pipeline.evaluate("BTC/USDT", num_open_positions=3)

    assert result is None
    pipeline.repo.append_event.assert_any_call(
        event_type="gate.max_positions.rejected",
        level="WARN",
        payload={
            "symbol": "BTC/USDT",
            "open_positions": 3,
            "max_allowed": 3,
        },
        public_safe=False,
    )


# --- Gate: Profitability rejects ---


@patch("quantsail_engine.core.entry_pipeline.check_volatility_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_spread_slippage_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_consecutive_losses", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.calculate_slippage", return_value=(50005.0, 0.5))
@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_profitability_gate_rejects(mock_atr, mock_slip, mock_cl, mock_ss, mock_vs, pipeline):
    """Profitability gate rejects unprofitable trade."""
    pipeline.profitability_gate.evaluate.return_value = (False, {"net_profit_usd": -2.0})

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)
    assert result is None


# --- Streak sizer reduces quantity ---


@patch("quantsail_engine.core.entry_pipeline.check_volatility_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_spread_slippage_spike", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.check_consecutive_losses", return_value=(False, None))
@patch("quantsail_engine.core.entry_pipeline.calculate_slippage", return_value=(50005.0, 0.5))
@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0] * 100)
def test_streak_sizer_reduces_quantity(mock_atr, mock_slip, mock_cl, mock_ss, mock_vs, pipeline):
    """Streak sizer multiplier < 1 reduces position size."""
    pipeline.streak_sizer.get_multiplier.return_value = 0.5
    pipeline.dynamic_sizer.calculate.return_value = 0.10

    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)

    assert result is not None
    assert result.quantity == pytest.approx(0.05, abs=0.001)


# --- Slippage estimation failure ---


@patch("quantsail_engine.core.entry_pipeline.calculate_atr", return_value=[200.0] * 100)
@patch("quantsail_engine.core.entry_pipeline.calculate_slippage", side_effect=ValueError("Insufficient liquidity"))
def test_slippage_error_rejects(mock_slip, mock_atr, pipeline):
    """Slippage estimation failure → None + event."""
    result = pipeline.evaluate("BTC/USDT", num_open_positions=0)

    assert result is None
    pipeline.repo.append_event.assert_any_call(
        event_type="gate.liquidity.rejected",
        level="WARN",
        payload={"symbol": "BTC/USDT", "reason": "Insufficient liquidity"},
        public_safe=False,
    )
