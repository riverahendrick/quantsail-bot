"""Donchian Channels indicator."""

from dataclasses import dataclass

from quantsail_engine.models.candle import Candle


@dataclass(frozen=True)
class DonchianChannels:
    """Donchian Channels output."""
    high: list[float]
    low: list[float]
    mid: list[float]


def calculate_donchian_channels(candles: list[Candle], period: int = 20) -> DonchianChannels:
    """
    Calculate Donchian Channels.

    Args:
        candles: List of candles.
        period: Lookback period.

    Returns:
        DonchianChannels object.
    """
    length = len(candles)
    high_channel = [0.0] * length
    low_channel = [0.0] * length
    mid_channel = [0.0] * length

    if length < period:
        return DonchianChannels(high_channel, low_channel, mid_channel)

    for i in range(period - 1, length):
        slice_candles = candles[i - period + 1 : i + 1]
        
        highest_high = max(c.high for c in slice_candles)
        lowest_low = min(c.low for c in slice_candles)
        
        high_channel[i] = highest_high
        low_channel[i] = lowest_low
        mid_channel[i] = (highest_high + lowest_low) / 2.0

    return DonchianChannels(high=high_channel, low=low_channel, mid=mid_channel)
