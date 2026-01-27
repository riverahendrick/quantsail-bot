"""Abstract signal provider interface."""

from abc import ABC, abstractmethod

from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import Signal


class SignalProvider(ABC):
    """Abstract interface for signal generation."""

    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
    ) -> Signal:
        """
        Generate a trading signal based on market data.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            candles: Historical OHLCV data
            orderbook: Current orderbook snapshot

        Returns:
            Trading signal (HOLD, ENTER_LONG, or EXIT)
        """
        ...
