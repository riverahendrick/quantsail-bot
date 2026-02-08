"""Tests for new indicators: VWAP, MACD, OBV."""

import math
from datetime import datetime

from quantsail_engine.indicators.macd import MACDResult, calculate_macd
from quantsail_engine.indicators.obv import calculate_obv
from quantsail_engine.indicators.vwap import calculate_vwap
from quantsail_engine.models.candle import Candle


def _candle(
    close: float,
    high: float,
    low: float,
    volume: float = 100.0,
    open_price: float | None = None,
) -> Candle:
    """Helper to build candles for tests."""
    return Candle(
        timestamp=datetime.now(),
        open=open_price if open_price is not None else close,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


# ── VWAP Tests ──────────────────────────────────────────────────────────


class TestVWAP:
    """VWAP indicator tests."""

    def test_empty_input(self) -> None:
        assert calculate_vwap([]) == []

    def test_single_candle(self) -> None:
        c = _candle(close=100.0, high=110.0, low=90.0, volume=1000.0)
        # Typical price = (110 + 90 + 100) / 3 = 100.0
        result = calculate_vwap([c])
        assert len(result) == 1
        assert result[0] == 100.0

    def test_two_candles(self) -> None:
        c1 = _candle(close=100.0, high=110.0, low=90.0, volume=1000.0)
        c2 = _candle(close=120.0, high=130.0, low=110.0, volume=2000.0)
        # TP1 = (110+90+100)/3 = 100. cum_tp_vol = 100*1000 = 100000, cum_vol = 1000
        # VWAP1 = 100000/1000 = 100.0
        # TP2 = (130+110+120)/3 = 120. cum_tp_vol = 100000+120*2000 = 340000, cum_vol = 3000
        # VWAP2 = 340000/3000 = 113.333...
        result = calculate_vwap([c1, c2])
        assert len(result) == 2
        assert result[0] == 100.0
        assert math.isclose(result[1], 113.3333, rel_tol=1e-3)

    def test_zero_volume_candle(self) -> None:
        c1 = _candle(close=100.0, high=110.0, low=90.0, volume=0.0)
        result = calculate_vwap([c1])
        assert result[0] == 0.0  # Cumulative volume is 0

    def test_zero_volume_then_nonzero(self) -> None:
        c1 = _candle(close=100.0, high=110.0, low=90.0, volume=0.0)
        c2 = _candle(close=120.0, high=130.0, low=110.0, volume=500.0)
        result = calculate_vwap([c1, c2])
        assert result[0] == 0.0
        # TP2 = 120, cum_tp_vol = 0 + 120*500 = 60000, cum_vol = 500
        assert result[1] == 120.0

    def test_multiple_candles_cumulative(self) -> None:
        candles = [
            _candle(close=100.0, high=105.0, low=95.0, volume=100.0),
            _candle(close=110.0, high=115.0, low=105.0, volume=200.0),
            _candle(close=105.0, high=110.0, low=100.0, volume=150.0),
        ]
        result = calculate_vwap(candles)
        assert len(result) == 3
        # VWAP is always cumulative => monotonic-ish based on weighted prices
        # Each value should be a valid price (between min low and max high)
        for v in result:
            assert v >= 0


# ── MACD Tests ──────────────────────────────────────────────────────────


class TestMACD:
    """MACD indicator tests."""

    def test_empty_input(self) -> None:
        result = calculate_macd([])
        assert result.macd_line == []
        assert result.signal_line == []
        assert result.histogram == []

    def test_insufficient_data(self) -> None:
        result = calculate_macd([1.0] * 10, fast_period=12, slow_period=26)
        assert len(result.macd_line) == 10
        assert all(v == 0.0 for v in result.macd_line)
        assert all(v == 0.0 for v in result.signal_line)
        assert all(v == 0.0 for v in result.histogram)

    def test_basic_calculation(self) -> None:
        # Generate enough data for MACD (need slow_period=26 minimum)
        values = [100.0 + i for i in range(40)]  # Trending up
        result = calculate_macd(values, fast_period=12, slow_period=26, signal_period=9)
        assert len(result.macd_line) == 40
        assert len(result.signal_line) == 40
        assert len(result.histogram) == 40

        # In an uptrend, MACD should be positive after enough data
        # The fast EMA reacts faster => fast > slow => positive MACD
        assert result.macd_line[-1] > 0

    def test_histogram_is_macd_minus_signal(self) -> None:
        values = [100.0 + i * 0.5 for i in range(50)]
        result = calculate_macd(values)
        for i in range(len(result.histogram)):
            expected = result.macd_line[i] - result.signal_line[i]
            assert math.isclose(result.histogram[i], expected, abs_tol=1e-10)

    def test_custom_periods(self) -> None:
        values = [50.0 + i for i in range(30)]
        result = calculate_macd(values, fast_period=5, slow_period=10, signal_period=3)
        assert len(result.macd_line) == 30
        # With shorter periods, we should have valid values sooner
        # After index 9 (slow_period-1), values should not be zero
        assert result.macd_line[-1] != 0.0

    def test_flat_market(self) -> None:
        # Use 200 values so EMAs fully converge past any zero-padding bias
        values = [100.0] * 200
        result = calculate_macd(values)
        # After fully converging, MACD should be very close to 0
        assert abs(result.macd_line[-1]) < 0.01
        assert abs(result.signal_line[-1]) < 0.01
        assert abs(result.histogram[-1]) < 0.01

    def test_result_type(self) -> None:
        result = calculate_macd([1.0] * 30)
        assert isinstance(result, MACDResult)


# ── OBV Tests ───────────────────────────────────────────────────────────


class TestOBV:
    """OBV indicator tests."""

    def test_empty_input(self) -> None:
        assert calculate_obv([]) == []

    def test_single_candle(self) -> None:
        c = _candle(close=100.0, high=110.0, low=90.0, volume=500.0)
        result = calculate_obv([c])
        assert result == [500.0]

    def test_price_up_adds_volume(self) -> None:
        c1 = _candle(close=100.0, high=110.0, low=90.0, volume=500.0)
        c2 = _candle(close=110.0, high=120.0, low=100.0, volume=300.0)
        result = calculate_obv([c1, c2])
        assert result == [500.0, 800.0]

    def test_price_down_subtracts_volume(self) -> None:
        c1 = _candle(close=110.0, high=120.0, low=100.0, volume=500.0)
        c2 = _candle(close=100.0, high=115.0, low=95.0, volume=200.0)
        result = calculate_obv([c1, c2])
        assert result == [500.0, 300.0]

    def test_price_unchanged_no_change(self) -> None:
        c1 = _candle(close=100.0, high=110.0, low=90.0, volume=500.0)
        c2 = _candle(close=100.0, high=105.0, low=95.0, volume=300.0)
        result = calculate_obv([c1, c2])
        assert result == [500.0, 500.0]

    def test_mixed_movements(self) -> None:
        candles = [
            _candle(close=100.0, high=110.0, low=90.0, volume=100.0),
            _candle(close=105.0, high=115.0, low=95.0, volume=200.0),   # up
            _candle(close=95.0, high=110.0, low=90.0, volume=150.0),    # down
            _candle(close=95.0, high=100.0, low=90.0, volume=50.0),     # flat
            _candle(close=110.0, high=115.0, low=95.0, volume=300.0),   # up
        ]
        result = calculate_obv(candles)
        # OBV[0] = 100
        # OBV[1] = 100 + 200 = 300 (up)
        # OBV[2] = 300 - 150 = 150 (down)
        # OBV[3] = 150 (flat)
        # OBV[4] = 150 + 300 = 450 (up)
        assert result == [100.0, 300.0, 150.0, 150.0, 450.0]

    def test_negative_obv_possible(self) -> None:
        candles = [
            _candle(close=100.0, high=110.0, low=90.0, volume=100.0),
            _candle(close=90.0, high=105.0, low=85.0, volume=500.0),    # big down
        ]
        result = calculate_obv(candles)
        assert result == [100.0, -400.0]

    def test_preserves_length(self) -> None:
        candles = [_candle(close=100.0 + i, high=110.0 + i, low=90.0 + i, volume=100.0) for i in range(20)]
        result = calculate_obv(candles)
        assert len(result) == 20
