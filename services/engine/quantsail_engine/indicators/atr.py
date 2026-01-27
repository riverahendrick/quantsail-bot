"""Average True Range (ATR) indicator."""

from quantsail_engine.models.candle import Candle


def calculate_atr(candles: list[Candle], period: int = 14) -> list[float]:
    """
    Calculate Average True Range (ATR).

    Args:
        candles: List of Candle objects.
        period: ATR period.

    Returns:
        List of ATR values.
    """
    length = len(candles)
    atr_values = [0.0] * length
    tr_values = [0.0] * length

    if length < period + 1:
        return atr_values

    # Calculate True Ranges
    # TR[0] is High[0] - Low[0] because there is no previous close
    tr_values[0] = candles[0].high - candles[0].low

    for i in range(1, length):
        high = candles[i].high
        low = candles[i].low
        prev_close = candles[i - 1].close
        
        tr_values[i] = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

    # First ATR is SMA of first 'period' TRs (or period+1?)
    # Usually first ATR is calculated at index `period-1` (0-based) using first `period` TRs
    # Wait, usually for Wilder's, we start at period.
    
    # 1. First ATR = SMA(TR, period)
    first_atr = sum(tr_values[:period]) / period
    atr_values[period - 1] = first_atr

    # 2. Subsequent ATR = (Prev ATR * (n-1) + Current TR) / n
    for i in range(period, length):
        atr_values[i] = (atr_values[i - 1] * (period - 1) + tr_values[i]) / period

    return atr_values
