"""Tests for technical indicators."""

import math
from datetime import datetime

from quantsail_engine.indicators.adx import calculate_adx
from quantsail_engine.indicators.atr import calculate_atr
from quantsail_engine.indicators.bollinger import calculate_bollinger_bands
from quantsail_engine.indicators.donchian import calculate_donchian_channels
from quantsail_engine.indicators.ema import calculate_ema
from quantsail_engine.indicators.rsi import calculate_rsi
from quantsail_engine.models.candle import Candle


def test_ema_calculation() -> None:
    values = [10.0, 11.0, 12.0, 13.0, 14.0]
    period = 3
    # SMA(3) = (10+11+12)/3 = 11.0. This is at index 2 (period-1).
    # Multiplier k = 2/(3+1) = 0.5
    # EMA[3] = (13 - 11) * 0.5 + 11 = 12.0
    # EMA[4] = (14 - 12) * 0.5 + 12 = 13.0
    
    ema = calculate_ema(values, period)
    assert ema[0] == 0.0
    assert ema[1] == 0.0
    assert ema[2] == 11.0
    assert ema[3] == 12.0
    assert ema[4] == 13.0


def test_rsi_calculation() -> None:
    # 5 data points -> 4 changes
    # period = 2
    # values: 10, 12, 11, 13, 15
    # changes: +2, -1, +2, +2
    # Gains: 2, 0, 2, 2
    # Losses: 0, 1, 0, 0
    
    values = [10.0, 12.0, 11.0, 13.0, 15.0]
    period = 2
    
    rsi = calculate_rsi(values, period)
    
    # Needs period+1 data points to have first RSI at index `period`
    # Index 0, 1: 0.0
    # Index 2: First RSI
    # Initial SMA of gains/losses (first 2 changes: +2, -1)
    # AvgGain = 2/2 = 1.0
    # AvgLoss = 1/2 = 0.5
    # RS = 2.0
    # RSI = 100 - 100/3 = 66.666...
    assert rsi[0] == 0.0
    assert rsi[1] == 0.0
    assert math.isclose(rsi[2], 66.66666666, rel_tol=1e-5)
    
    # Next step (change +2)
    # Prev AvgGain = 1.0, Prev AvgLoss = 0.5
    # New AvgGain = (1.0 * 1 + 2.0) / 2 = 1.5
    # New AvgLoss = (0.5 * 1 + 0.0) / 2 = 0.25
    # RS = 6.0
    # RSI = 100 - 100/7 = 85.714...
    assert math.isclose(rsi[3], 85.714285, rel_tol=1e-5)


def test_bollinger_bands() -> None:
    values = [10.0, 10.0, 10.0, 14.0, 14.0]
    period = 3
    std_dev_mult = 2.0
    
    bb = calculate_bollinger_bands(values, period, std_dev_mult)
    
    # Index 2: [10, 10, 10] -> SMA=10, SD=0 -> Upper=10, Lower=10
    assert bb.mid[2] == 10.0
    assert bb.upper[2] == 10.0
    assert bb.lower[2] == 10.0
    
    # Index 3: [10, 10, 14] -> SMA=11.333
    # Population Variance = 3.555... -> SD = 1.8856...
    # Upper = 11.333 + 2 * 1.8856 = 11.333 + 3.771 = 15.104
    assert math.isclose(bb.mid[3], 11.333333, rel_tol=1e-5)
    assert math.isclose(bb.upper[3], 15.1045, rel_tol=1e-3)


def test_indicators_insufficient_data() -> None:
    # EMA
    assert calculate_ema([], 5) == []
    assert calculate_ema([1.0], 5) == [0.0]
    
    # RSI
    assert calculate_rsi([], 14) == []
    assert calculate_rsi([1.0]*10, 14) == [0.0]*10
    
    # Bollinger
    bb = calculate_bollinger_bands([], 20)
    assert bb.mid == []
    bb = calculate_bollinger_bands([1.0]*10, 20)
    assert len(bb.mid) == 10
    assert bb.mid[0] == 0.0
    
    # ATR
    candles = [make_candle(10, 10, 10)]
    atr = calculate_atr(candles, 14)
    assert len(atr) == 1
    assert atr[0] == 0.0
    
    # ADX
    adx = calculate_adx(candles, 14)
    assert len(adx) == 1
    assert adx[0] == 0.0
    
    # Donchian
    dc = calculate_donchian_channels(candles, 20)
    assert len(dc.high) == 1
    assert dc.high[0] == 0.0


def make_candle(close: float, high: float, low: float) -> Candle:
    return Candle(
        timestamp=datetime.now(),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=100.0
    )


def test_atr_calculation() -> None:
    # Candles: (H, L, C)
    # 1: 10, 8, 9 (TR=2)
    # 2: 12, 11, 12 (TR=max(1, 3, 2)=3) | H-L=1, H-Cp=3, L-Cp=2
    
    c1 = make_candle(9, 10, 8)
    c2 = make_candle(12, 12, 11)
    candles = [c1, c2]
    
    # Period 1 for simplicity
    atr = calculate_atr(candles, period=1)
    # First ATR at index 0 (period-1) = TR[0] = 2.0? 
    # My impl: first ATR is SMA(TR, period) at index period-1.
    # TR list: [2.0, 3.0]
    # SMA(1) of [2.0] = 2.0 at index 0
    # Next ATR: (2.0 * 0 + 3.0) / 1 = 3.0
    
    assert atr[0] == 2.0
    assert atr[1] == 3.0


def test_donchian_calculation() -> None:
    # Highs: 10, 15, 12
    # Lows: 8, 11, 10
    c1 = make_candle(9, 10, 8)
    c2 = make_candle(13, 15, 11)
    c3 = make_candle(11, 12, 10)
    candles = [c1, c2, c3]
    
    period = 2
    dc = calculate_donchian_channels(candles, period)
    
    # Index 1 (range 0..1): MaxH(10, 15)=15, MinL(8, 11)=8
    assert dc.high[1] == 15.0
    assert dc.low[1] == 8.0
    assert dc.mid[1] == 11.5
    
    # Index 2 (range 1..2): MaxH(15, 12)=15, MinL(11, 10)=10
    assert dc.high[2] == 15.0
    assert dc.low[2] == 10.0


def test_adx_calculation_smoke() -> None:
    # ADX is complex, just ensure it runs and returns sensible range
    candles = [make_candle(100 + i, 105 + i, 95 + i) for i in range(50)]
    adx = calculate_adx(candles, period=14)
    assert len(adx) == 50
    # Last value should be > 0 and <= 100
    assert 0 <= adx[-1] <= 100
