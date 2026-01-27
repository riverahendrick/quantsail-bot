"""Abstract market data provider interface."""

from abc import ABC, abstractmethod

from quantsail_engine.models.candle import Candle, Orderbook


class MarketDataProvider(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """
        Fetch OHLCV candles for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Candle timeframe (e.g., "1m", "5m", "1h")
            limit: Number of candles to fetch

        Returns:
            List of candles, most recent last
        """
        ...

    @abstractmethod
    def get_orderbook(self, symbol: str, depth_levels: int) -> Orderbook:
        """
        Fetch orderbook snapshot for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            depth_levels: Number of price levels to fetch per side

        Returns:
            Orderbook with bids and asks
        """
        ...
