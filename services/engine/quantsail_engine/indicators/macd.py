"""Moving Average Convergence Divergence (MACD) indicator."""

from dataclasses import dataclass

from quantsail_engine.indicators.ema import calculate_ema


@dataclass
class MACDResult:
    """Container for MACD calculation results."""

    macd_line: list[float]
    signal_line: list[float]
    histogram: list[float]


def calculate_macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDResult:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(signal) of MACD Line
    Histogram = MACD Line - Signal Line

    Args:
        values: List of values (e.g., closing prices).
        fast_period: Fast EMA period (default: 12).
        slow_period: Slow EMA period (default: 26).
        signal_period: Signal EMA period (default: 9).

    Returns:
        MACDResult with macd_line, signal_line, and histogram.
        Early values (before enough data) will be 0.0.
    """
    if not values:
        return MACDResult(macd_line=[], signal_line=[], histogram=[])

    if len(values) < slow_period:
        n = len(values)
        return MACDResult(
            macd_line=[0.0] * n,
            signal_line=[0.0] * n,
            histogram=[0.0] * n,
        )

    # Calculate fast and slow EMAs
    ema_fast = calculate_ema(values, fast_period)
    ema_slow = calculate_ema(values, slow_period)

    # MACD line = fast EMA - slow EMA
    macd_line = [
        fast - slow for fast, slow in zip(ema_fast, ema_slow)
    ]

    # Signal line = EMA of MACD line
    signal_line = calculate_ema(macd_line, signal_period)

    # Histogram = MACD - Signal
    histogram = [m - s for m, s in zip(macd_line, signal_line)]

    return MACDResult(
        macd_line=macd_line,
        signal_line=signal_line,
        histogram=histogram,
    )
