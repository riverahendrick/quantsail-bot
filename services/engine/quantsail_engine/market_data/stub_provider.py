"""Stub market data provider for testing with deterministic data."""

from datetime import datetime, timedelta, timezone

from quantsail_engine.models.candle import Candle, Orderbook

from .provider import MarketDataProvider


class StubMarketDataProvider(MarketDataProvider):
    """Stub provider returning fixed market data for testing."""

    def __init__(
        self,
        base_price: float = 50000.0,
        spread_bps: float = 2.0,  # 2 basis points = 0.02%
        volume: float = 100.0,
    ):
        """
        Initialize stub provider with configurable parameters.

        Args:
            base_price: Base price for the asset
            spread_bps: Spread in basis points (1 bp = 0.01%)
            volume: Volume for candles
        """
        self.base_price = base_price
        self.spread_bps = spread_bps
        self.volume = volume

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Return deterministic candle data."""
        candles: list[Candle] = []
        base_time = datetime.now(timezone.utc)

        for i in range(limit):
            # Create realistic OHLC pattern
            timestamp = base_time - timedelta(minutes=(limit - i) * 5)
            open_price = self.base_price
            high_price = self.base_price * 1.001  # +0.1%
            low_price = self.base_price * 0.999  # -0.1%
            close_price = self.base_price * 1.0005  # +0.05%

            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=self.volume,
                )
            )

        return candles

    def get_orderbook(self, symbol: str, depth_levels: int) -> Orderbook:
        """Return deterministic orderbook data."""
        spread = self.base_price * (self.spread_bps / 10000.0)
        mid_price = self.base_price

        best_bid = mid_price - (spread / 2)
        best_ask = mid_price + (spread / 2)

        # Create price levels with decreasing size
        bids = []
        asks = []

        for i in range(depth_levels):
            # Bids go down from best bid
            bid_price = best_bid - (i * spread)
            bid_qty = 10.0 * (depth_levels - i)  # Larger size at better prices
            bids.append((bid_price, bid_qty))

            # Asks go up from best ask
            ask_price = best_ask + (i * spread)
            ask_qty = 10.0 * (depth_levels - i)
            asks.append((ask_price, ask_qty))

        return Orderbook(bids=bids, asks=asks)
