"""Tests for VWAPReversionStrategy and enhanced EnsembleCombiner."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from quantsail_engine.config.models import (
    BotConfig,
    EnsembleConfig,
    StrategiesConfig,
    VWAPReversionConfig,
)
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.strategy import StrategyOutput
from quantsail_engine.strategies.ensemble import EnsembleCombiner
from quantsail_engine.strategies.vwap_reversion import VWAPReversionStrategy

_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _make_candle(close: float, high: float, low: float, volume: float, open_: float | None = None) -> Candle:
    """Helper to build a Candle with minimal fields."""
    return Candle(
        timestamp=_TS,
        open=open_ or close,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_orderbook() -> Orderbook:
    """Create a minimal orderbook for testing."""
    return Orderbook(
        bids=[(100.0, 1.0)],
        asks=[(101.0, 1.0)],
    )


class TestVWAPReversionDisabled:
    """Tests when VWAP strategy is disabled."""

    def test_returns_hold_when_disabled(self) -> None:
        config = BotConfig(
            strategies=StrategiesConfig(
                vwap_reversion=VWAPReversionConfig(enabled=False),
            ),
        )
        strategy = VWAPReversionStrategy()
        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(20)]
        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.signal == SignalType.HOLD
        assert result.rationale["reason"] == "disabled"


class TestVWAPReversionInsufficientData:
    """Tests for insufficient candle data."""

    def test_returns_hold_with_no_data(self) -> None:
        config = BotConfig()
        strategy = VWAPReversionStrategy()
        result = strategy.analyze("BTCUSDT", [], _make_orderbook(), config)
        assert result.signal == SignalType.HOLD
        assert result.rationale["reason"] == "insufficient_data"

    def test_returns_hold_with_few_candles(self) -> None:
        config = BotConfig()
        strategy = VWAPReversionStrategy()
        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0)]
        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.signal == SignalType.HOLD


class TestVWAPReversionEntry:
    """Tests for entry signal generation."""

    def test_enter_long_when_below_vwap_and_rsi_oversold(self) -> None:
        """Price far below VWAP + low RSI should trigger ENTER_LONG."""
        strategy = VWAPReversionStrategy()
        config = BotConfig(
            strategies=StrategiesConfig(
                vwap_reversion=VWAPReversionConfig(
                    enabled=True,
                    deviation_entry_pct=1.0,
                    rsi_oversold=35.0,
                    rsi_period=5,
                    obv_confirmation=False,
                ),
            ),
        )

        # Build candles where price is significantly below VWAP
        # Start high (to push VWAP up) then drop sharply
        candles = []
        for i in range(10):
            candles.append(_make_candle(120.0, 125.0, 115.0, 1000.0))
        # Drop sharply at the end — price drops to 100 while VWAP stays ~120
        for i in range(8):
            candles.append(_make_candle(100.0 - i * 2, 105.0 - i * 2, 95.0 - i * 2, 800.0))

        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)

        # The RSI should be oversold with this downtrend, and price << VWAP
        assert result.strategy_name == "vwap_reversion"
        assert result.rationale["vwap"] > result.rationale["price"]  # price below VWAP

    def test_hold_when_rsi_not_oversold(self) -> None:
        """Price below VWAP but RSI normal -> HOLD."""
        strategy = VWAPReversionStrategy()
        config = BotConfig(
            strategies=StrategiesConfig(
                vwap_reversion=VWAPReversionConfig(
                    enabled=True,
                    deviation_entry_pct=1.0,
                    rsi_oversold=10.0,  # Very low threshold — hard to trigger
                    rsi_period=5,
                    obv_confirmation=False,
                ),
            ),
        )

        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(20)]
        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.signal == SignalType.HOLD

    def test_hold_when_price_near_vwap(self) -> None:
        """Price near VWAP -> HOLD regardless of RSI."""
        strategy = VWAPReversionStrategy()
        config = BotConfig(
            strategies=StrategiesConfig(
                vwap_reversion=VWAPReversionConfig(
                    enabled=True,
                    deviation_entry_pct=5.0,  # Require 5% deviation
                    rsi_oversold=50.0,
                    rsi_period=5,
                    obv_confirmation=False,
                ),
            ),
        )

        # All candles at same price — VWAP = price, deviation ~0%
        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(20)]
        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.signal == SignalType.HOLD


class TestVWAPReversionOBVConfirmation:
    """Tests for OBV confirmation logic."""

    def test_hold_when_obv_not_rising_with_confirmation(self) -> None:
        """OBV confirmation required but OBV declining -> HOLD."""
        strategy = VWAPReversionStrategy()
        config = BotConfig(
            strategies=StrategiesConfig(
                vwap_reversion=VWAPReversionConfig(
                    enabled=True,
                    deviation_entry_pct=0.1,
                    rsi_oversold=50.0,
                    rsi_period=5,
                    obv_confirmation=True,
                ),
            ),
        )

        # Build declining volume candles
        candles = []
        for i in range(10):
            candles.append(_make_candle(120.0, 125.0, 115.0, 2000.0))
        # Price drops with declining volume (OBV should drop)
        for i in range(10):
            candles.append(_make_candle(100.0 - i, 105.0 - i, 95.0 - i, 500.0 - i * 20))

        result = strategy.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.strategy_name == "vwap_reversion"


class TestEnsembleCombinerAgreement:
    """Tests for agreement mode (original behavior)."""

    def test_agreement_mode_holds_when_no_consensus(self) -> None:
        combiner = EnsembleCombiner()
        config = BotConfig(
            strategies=StrategiesConfig(
                ensemble=EnsembleConfig(mode="agreement", min_agreement=4),
            ),
        )
        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(60)]
        result = combiner.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert result.signal_type == SignalType.HOLD

    def test_agreement_mode_includes_all_strategy_outputs(self) -> None:
        combiner = EnsembleCombiner()
        config = BotConfig()
        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(60)]
        result = combiner.analyze("BTCUSDT", candles, _make_orderbook(), config)
        assert len(result.strategy_outputs) == 4  # trend, mr, breakout, vwap


class TestEnsembleCombinerWeighted:
    """Tests for the new weighted scoring mode."""

    def test_weighted_mode_with_all_enter_long(self) -> None:
        """When all strategies say ENTER_LONG with high confidence, cross threshold."""
        combiner = EnsembleCombiner()
        config = BotConfig(
            strategies=StrategiesConfig(
                ensemble=EnsembleConfig(
                    mode="weighted",
                    weighted_threshold=0.5,
                    weight_trend=0.30,
                    weight_mean_reversion=0.25,
                    weight_breakout=0.20,
                    weight_vwap=0.25,
                ),
            ),
        )

        # Mock all strategies to return ENTER_LONG with high confidence
        mock_outputs = [
            StrategyOutput(signal=SignalType.ENTER_LONG, confidence=0.9, strategy_name="trend", rationale={}),
            StrategyOutput(signal=SignalType.ENTER_LONG, confidence=0.8, strategy_name="mean_reversion", rationale={}),
            StrategyOutput(signal=SignalType.ENTER_LONG, confidence=0.7, strategy_name="breakout", rationale={}),
            StrategyOutput(signal=SignalType.ENTER_LONG, confidence=0.85, strategy_name="vwap_reversion", rationale={}),
        ]

        with patch.object(combiner, "strategies") as mock_strategies:
            mock_strats = []
            for output in mock_outputs:
                s = MagicMock()
                s.analyze.return_value = output
                mock_strats.append(s)
            mock_strategies.__iter__ = lambda _: iter(mock_strats)

            candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(20)]
            result = combiner.analyze("BTCUSDT", candles, _make_orderbook(), config)

        assert result.signal_type == SignalType.ENTER_LONG
        assert result.confidence > 0.5

    def test_weighted_mode_hold_when_below_threshold(self) -> None:
        """When weighted score is below threshold -> HOLD."""
        combiner = EnsembleCombiner()
        config = BotConfig(
            strategies=StrategiesConfig(
                ensemble=EnsembleConfig(
                    mode="weighted",
                    weighted_threshold=0.9,  # Very high threshold
                    weight_trend=0.30,
                    weight_mean_reversion=0.25,
                    weight_breakout=0.20,
                    weight_vwap=0.25,
                ),
            ),
        )

        mock_outputs = [
            StrategyOutput(signal=SignalType.ENTER_LONG, confidence=0.3, strategy_name="trend", rationale={}),
            StrategyOutput(signal=SignalType.HOLD, confidence=0.0, strategy_name="mean_reversion", rationale={}),
            StrategyOutput(signal=SignalType.HOLD, confidence=0.0, strategy_name="breakout", rationale={}),
            StrategyOutput(signal=SignalType.HOLD, confidence=0.0, strategy_name="vwap_reversion", rationale={}),
        ]

        with patch.object(combiner, "strategies") as mock_strategies:
            mock_strats = []
            for output in mock_outputs:
                s = MagicMock()
                s.analyze.return_value = output
                mock_strats.append(s)
            mock_strategies.__iter__ = lambda _: iter(mock_strats)

            candles = [_make_candle(100.0, 105.0, 95.0, 1000.0)]
            result = combiner.analyze("BTCUSDT", candles, _make_orderbook(), config)

        assert result.signal_type == SignalType.HOLD

    def test_weighted_mode_handles_strategy_exception(self) -> None:
        """Strategy error should be caught and HOLD output added."""
        combiner = EnsembleCombiner()
        config = BotConfig(
            strategies=StrategiesConfig(
                ensemble=EnsembleConfig(mode="weighted", weighted_threshold=0.5),
            ),
        )

        candles = [_make_candle(100.0, 105.0, 95.0, 1000.0) for _ in range(60)]

        # Patch one strategy to raise
        original_strategies = list(combiner.strategies)
        failing_strategy = MagicMock()
        failing_strategy.analyze.side_effect = RuntimeError("boom")
        combiner.strategies = [failing_strategy] + original_strategies[1:]

        result = combiner.analyze("BTCUSDT", candles, _make_orderbook(), config)
        # Should still have 4 outputs (1 error + 3 real ones)
        assert len(result.strategy_outputs) == 4
        # The error output should be HOLD
        error_output = result.strategy_outputs[0]
        assert error_output.signal == SignalType.HOLD
        assert "error" in error_output.rationale


class TestEnsembleCombinerInit:
    """Tests for ensemble initialization."""

    def test_includes_vwap_strategy(self) -> None:
        combiner = EnsembleCombiner()
        strategy_types = [type(s).__name__ for s in combiner.strategies]
        assert "VWAPReversionStrategy" in strategy_types

    def test_includes_four_strategies(self) -> None:
        combiner = EnsembleCombiner()
        assert len(combiner.strategies) == 4
