"""Volume Weighted Average Price (VWAP) indicator."""

from quantsail_engine.models.candle import Candle


def calculate_vwap(candles: list[Candle]) -> list[float]:
    """
    Calculate Volume Weighted Average Price (VWAP).

    VWAP = Cumulative(Typical_Price * Volume) / Cumulative(Volume)
    Typical_Price = (High + Low + Close) / 3

    Args:
        candles: List of Candle objects with high, low, close, volume.

    Returns:
        List of VWAP values (same length as input).
        Values before sufficient data are 0.0.
    """
    if not candles:
        return []

    vwap_values: list[float] = []
    cumulative_tp_vol = 0.0
    cumulative_vol = 0.0

    for candle in candles:
        typical_price = (candle.high + candle.low + candle.close) / 3.0
        cumulative_tp_vol += typical_price * candle.volume
        cumulative_vol += candle.volume

        if cumulative_vol > 0:
            vwap_values.append(cumulative_tp_vol / cumulative_vol)
        else:
            vwap_values.append(0.0)

    return vwap_values
