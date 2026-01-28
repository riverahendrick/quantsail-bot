"""Unit tests for circuit breaker trigger functions."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from quantsail_engine.breakers.triggers import (
    check_consecutive_losses,
    check_exchange_instability,
    check_spread_slippage_spike,
    check_volatility_spike,
)
from quantsail_engine.config.models import (
    ConsecutiveLossesBreakerConfig,
    ExchangeInstabilityBreakerConfig,
    SpreadSlippageBreakerConfig,
    VolatilityBreakerConfig,
)
from quantsail_engine.models.candle import Candle, Orderbook


def test_volatility_spike_trigger() -> None:
    """Test volatility spike triggers when candle range exceeds ATR threshold."""
    config = VolatilityBreakerConfig(enabled=True, atr_multiple_pause=3.0)
    candles = [
        Candle(datetime.now(timezone.utc), 100.0, 105.0, 98.0, 103.0, 1000.0),
    ]
    atr_values = [2.0]  # ATR = 2.0, threshold = 6.0, candle range = 7.0

    should_trigger, context = check_volatility_spike(config, "BTC/USDT", candles, atr_values)

    assert should_trigger is True
    assert context is not None
    assert context["candle_range"] == 7.0
    assert context["atr"] == 2.0
    assert context["atr_multiple"] == 3.5
    assert context["threshold"] == 6.0


def test_volatility_spike_no_trigger() -> None:
    """Test volatility spike does not trigger when within threshold."""
    config = VolatilityBreakerConfig(enabled=True, atr_multiple_pause=3.0)
    candles = [
        Candle(datetime.now(timezone.utc), 100.0, 102.0, 99.0, 101.0, 1000.0),
    ]
    atr_values = [2.0]  # ATR = 2.0, threshold = 6.0, candle range = 3.0

    should_trigger, context = check_volatility_spike(config, "BTC/USDT", candles, atr_values)

    assert should_trigger is False
    assert context is None


def test_volatility_spike_disabled() -> None:
    """Test volatility spike disabled in config returns no trigger."""
    config = VolatilityBreakerConfig(enabled=False)
    candles = [
        Candle(datetime.now(timezone.utc), 100.0, 200.0, 50.0, 150.0, 1000.0),
    ]
    atr_values = [2.0]

    should_trigger, context = check_volatility_spike(config, "BTC/USDT", candles, atr_values)

    assert should_trigger is False
    assert context is None


def test_volatility_spike_zero_atr() -> None:
    """Test volatility spike with zero ATR returns no trigger."""
    config = VolatilityBreakerConfig(enabled=True, atr_multiple_pause=3.0)
    candles = [
        Candle(datetime.now(timezone.utc), 100.0, 105.0, 95.0, 100.0, 1000.0),
    ]
    atr_values = [0.0]

    should_trigger, context = check_volatility_spike(config, "BTC/USDT", candles, atr_values)

    assert should_trigger is False
    assert context is None


def test_volatility_spike_empty_data() -> None:
    """Test volatility spike with empty candles/ATR returns no trigger."""
    config = VolatilityBreakerConfig(enabled=True, atr_multiple_pause=3.0)

    should_trigger, context = check_volatility_spike(config, "BTC/USDT", [], [])

    assert should_trigger is False
    assert context is None


def test_spread_spike_trigger() -> None:
    """Test spread spike triggers when spread exceeds basis points threshold."""
    config = SpreadSlippageBreakerConfig(enabled=True, max_spread_bps=50.0)
    orderbook = Orderbook(
        bids=[(99.0, 10.0)],
        asks=[(101.0, 10.0)],
    )
    # Mid = 100.0, spread = 2.0, spread_bps = (2.0 / 100.0) * 10000 = 200.0

    should_trigger, context = check_spread_slippage_spike(config, "BTC/USDT", orderbook, None)

    assert should_trigger is True
    assert context is not None
    assert context["spread_bps"] == 200.0
    assert context["max_spread_bps"] == 50.0
    assert context["best_bid"] == 99.0
    assert context["best_ask"] == 101.0
    assert context["mid_price"] == 100.0


def test_spread_spike_no_trigger() -> None:
    """Test spread spike does not trigger when within threshold."""
    config = SpreadSlippageBreakerConfig(enabled=True, max_spread_bps=50.0)
    orderbook = Orderbook(
        bids=[(99.8, 10.0)],
        asks=[(100.0, 10.0)],
    )
    # Mid = 99.9, spread = 0.2, spread_bps = (0.2 / 99.9) * 10000 = ~20.02

    should_trigger, context = check_spread_slippage_spike(config, "BTC/USDT", orderbook, None)

    assert should_trigger is False
    assert context is None


def test_spread_spike_disabled() -> None:
    """Test spread spike disabled in config returns no trigger."""
    config = SpreadSlippageBreakerConfig(enabled=False)
    orderbook = Orderbook(
        bids=[(50.0, 10.0)],
        asks=[(150.0, 10.0)],
    )

    should_trigger, context = check_spread_slippage_spike(config, "BTC/USDT", orderbook, None)

    assert should_trigger is False
    assert context is None


def test_spread_spike_zero_mid_price() -> None:
    """Test spread spike with zero mid price returns no trigger."""
    config = SpreadSlippageBreakerConfig(enabled=True, max_spread_bps=50.0)
    # Create mock orderbook with zero mid price
    orderbook = MagicMock()
    orderbook.mid_price = 0.0

    should_trigger, context = check_spread_slippage_spike(config, "BTC/USDT", orderbook, None)

    assert should_trigger is False
    assert context is None


def test_consecutive_losses_trigger() -> None:
    """Test consecutive losses triggers when threshold exceeded."""
    config = ConsecutiveLossesBreakerConfig(enabled=True, max_losses=3)
    repo = MagicMock()
    now = datetime.now(timezone.utc)
    repo.get_recent_closed_trades.return_value = [
        {"id": "trade3", "realized_pnl_usd": -10.0, "pnl_pct": -1.0, "closed_at": now},
        {"id": "trade2", "realized_pnl_usd": -5.0, "pnl_pct": -0.5, "closed_at": now},
        {"id": "trade1", "realized_pnl_usd": -8.0, "pnl_pct": -0.8, "closed_at": now},
        {"id": "trade0", "realized_pnl_usd": 20.0, "pnl_pct": 2.0, "closed_at": now},
    ]

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is True
    assert context is not None
    assert context["consecutive_losses"] == 3
    assert context["max_losses"] == 3
    assert context["losing_trade_ids"] == ["trade3", "trade2", "trade1"]


def test_consecutive_losses_no_trigger() -> None:
    """Test consecutive losses does not trigger when below threshold."""
    config = ConsecutiveLossesBreakerConfig(enabled=True, max_losses=3)
    repo = MagicMock()
    now = datetime.now(timezone.utc)
    repo.get_recent_closed_trades.return_value = [
        {"id": "trade2", "realized_pnl_usd": -10.0, "pnl_pct": -1.0, "closed_at": now},
        {"id": "trade1", "realized_pnl_usd": -5.0, "pnl_pct": -0.5, "closed_at": now},
        {"id": "trade0", "realized_pnl_usd": 20.0, "pnl_pct": 2.0, "closed_at": now},
    ]

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is False
    assert context is None


def test_consecutive_losses_reset_on_win() -> None:
    """Test consecutive losses count resets at first winning trade."""
    config = ConsecutiveLossesBreakerConfig(enabled=True, max_losses=3)
    repo = MagicMock()
    now = datetime.now(timezone.utc)
    repo.get_recent_closed_trades.return_value = [
        {"id": "trade4", "realized_pnl_usd": -10.0, "pnl_pct": -1.0, "closed_at": now},
        {"id": "trade3", "realized_pnl_usd": -5.0, "pnl_pct": -0.5, "closed_at": now},
        # Win stops count
        {"id": "trade2", "realized_pnl_usd": 15.0, "pnl_pct": 1.5, "closed_at": now},
        {"id": "trade1", "realized_pnl_usd": -8.0, "pnl_pct": -0.8, "closed_at": now},
        {"id": "trade0", "realized_pnl_usd": -12.0, "pnl_pct": -1.2, "closed_at": now},
    ]

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is False
    assert context is None


def test_consecutive_losses_disabled() -> None:
    """Test consecutive losses disabled in config returns no trigger."""
    config = ConsecutiveLossesBreakerConfig(enabled=False)
    repo = MagicMock()

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is False
    assert context is None


def test_consecutive_losses_no_trades() -> None:
    """Test consecutive losses with no trades returns no trigger."""
    config = ConsecutiveLossesBreakerConfig(enabled=True, max_losses=3)
    repo = MagicMock()
    repo.get_recent_closed_trades.return_value = []

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is False
    assert context is None


def test_consecutive_losses_zero_pnl() -> None:
    """Test consecutive losses with zero PnL (breakeven) stops count."""
    config = ConsecutiveLossesBreakerConfig(enabled=True, max_losses=3)
    repo = MagicMock()
    now = datetime.now(timezone.utc)
    repo.get_recent_closed_trades.return_value = [
        {"id": "trade2", "realized_pnl_usd": -10.0, "pnl_pct": -1.0, "closed_at": now},
        # Breakeven stops count
        {"id": "trade1", "realized_pnl_usd": 0.0, "pnl_pct": 0.0, "closed_at": now},
        {"id": "trade0", "realized_pnl_usd": -5.0, "pnl_pct": -0.5, "closed_at": now},
    ]

    should_trigger, context = check_consecutive_losses(config, repo)

    assert should_trigger is False
    assert context is None


def test_exchange_instability_stub() -> None:
    """Test exchange instability always returns False (MVP stub)."""
    config = ExchangeInstabilityBreakerConfig(enabled=True)

    should_trigger, context = check_exchange_instability(config)

    assert should_trigger is False
    assert context is None
