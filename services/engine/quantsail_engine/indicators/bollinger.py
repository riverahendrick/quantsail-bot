"""Bollinger Bands indicator."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BollingerBands:
    """Bollinger Bands output."""
    mid: list[float]
    upper: list[float]
    lower: list[float]


def calculate_bollinger_bands(
    values: list[float], period: int = 20, std_dev_mult: float = 2.0
) -> BollingerBands:
    """
    Calculate Bollinger Bands.

    Args:
        values: List of closing prices.
        period: SMA period.
        std_dev_mult: Standard deviation multiplier.

    Returns:
        BollingerBands object with lists.
    """
    length = len(values)
    mid = [0.0] * length
    upper = [0.0] * length
    lower = [0.0] * length

    if length < period:
        return BollingerBands(mid, upper, lower)

    for i in range(period - 1, length):
        # Slice including i
        slice_vals = values[i - period + 1 : i + 1]
        
        # Calculate SMA (Mid Band)
        sma = sum(slice_vals) / period
        mid[i] = sma

        # Calculate Standard Deviation
        variance = sum((x - sma) ** 2 for x in slice_vals) / period
        std_dev = math.sqrt(variance)

        upper[i] = sma + (std_dev * std_dev_mult)
        lower[i] = sma - (std_dev * std_dev_mult)

    return BollingerBands(mid=mid, upper=upper, lower=lower)
