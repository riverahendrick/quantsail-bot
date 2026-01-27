"""Coverage tests for indicators."""

from quantsail_engine.indicators.adx import calculate_adx
from quantsail_engine.indicators.rsi import calculate_rsi
from tests.test_indicators import make_candle


def test_adx_edge_cases() -> None:
    # 1. Down move > Up move (plus_dm = 0)
    c1 = make_candle(9, 10, 8)
    c2 = make_candle(7, 10, 5) # Up=0, Down=3
    adx = calculate_adx([c1, c2], 14)
    assert len(adx) == 2
    
    # 2. Up move > Down move (minus_dm = 0)
    c3 = make_candle(9, 10, 8)
    c4 = make_candle(11, 12, 8) # Up=2, Down=0
    adx_up = calculate_adx([c3, c4], 14)
    assert len(adx_up) == 2
    
    # 3. Flat market (sum_di = 0)
    flat_candles = [make_candle(10, 10, 10) for _ in range(30)]
    adx_flat = calculate_adx(flat_candles, 14)
    assert adx_flat[-1] == 0.0
    
    # 4. Insufficient for ADX but sufficient for TR/DM
    candles_short = [make_candle(10, 12, 8) for _ in range(3)]
    adx_short = calculate_adx(candles_short, 2)
    assert adx_short[-1] == 0.0


    # 5. Up > 0 but Up < Down (plus_dm = 0)
    c5 = make_candle(10, 10, 10)
    c6 = make_candle(10, 12, 5) # Up=2, Down=5
    adx_mixed = calculate_adx([c5, c6], 14)
    assert len(adx_mixed) == 2


def test_rsi_edge_cases() -> None:
    # Pure gains -> AvgLoss = 0 -> RSI = 100
    values = [10.0, 11.0, 12.0, 13.0, 14.0]
    period = 2
    rsi = calculate_rsi(values, period)
    assert rsi[2] == 100.0
    assert rsi[3] == 100.0
