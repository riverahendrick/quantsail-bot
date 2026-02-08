"""On-Balance Volume (OBV) indicator."""

from quantsail_engine.models.candle import Candle


def calculate_obv(candles: list[Candle]) -> list[float]:
    """
    Calculate On-Balance Volume (OBV).

    OBV is a cumulative volume indicator:
    - If close > previous close: OBV += volume
    - If close < previous close: OBV -= volume
    - If close == previous close: OBV unchanged

    Args:
        candles: List of Candle objects with close and volume.

    Returns:
        List of OBV values (same length as input).
        First value is the first candle's volume.
    """
    if not candles:
        return []

    obv_values: list[float] = [candles[0].volume]

    for i in range(1, len(candles)):
        if candles[i].close > candles[i - 1].close:
            obv_values.append(obv_values[-1] + candles[i].volume)
        elif candles[i].close < candles[i - 1].close:
            obv_values.append(obv_values[-1] - candles[i].volume)
        else:
            obv_values.append(obv_values[-1])

    return obv_values
