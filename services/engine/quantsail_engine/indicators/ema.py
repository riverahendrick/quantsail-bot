"""Exponential Moving Average (EMA) indicator."""

def calculate_ema(values: list[float], period: int) -> list[float]:
    """
    Calculate Exponential Moving Average (EMA).

    Args:
        values: List of values (e.g., closing prices).
        period: EMA period.

    Returns:
        List of EMA values (same length as input).
        First (period-1) values will be None or approximated.
        We use SMA for the first value.
        For simplicity in this engine, we pad the beginning with None or the first value.
        Wait, returning None complicates type hints. Let's return 0.0 or
        better: the first valid EMA is at index (period-1).
        
        To match standard behavior:
        - First valid value at index `period - 1` is SMA.
        - Subsequent values use EMA formula.
        - Preceding values are 0.0 (or we can return a list of Optional[float]).
        
        Let's return 0.0 for initial values to keep it simple float list, 
        but caller must know to ignore them.
    """
    if not values:
        return []
    
    if len(values) < period:
        return [0.0] * len(values)

    ema_values = [0.0] * len(values)
    
    # First valid EMA is SMA of first 'period' values
    sma = sum(values[:period]) / period
    ema_values[period - 1] = sma

    multiplier = 2.0 / (period + 1)

    for i in range(period, len(values)):
        ema_values[i] = (values[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]

    return ema_values
