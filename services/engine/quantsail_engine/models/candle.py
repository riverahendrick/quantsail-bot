"""Market data models for candles and orderbook."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    """OHLCV candle data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        """Validate candle data integrity."""
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("High must be >= open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("Low must be <= open, close, and high")
        if self.volume < 0:
            raise ValueError("Volume must be non-negative")


@dataclass(frozen=True)
class Orderbook:
    """Orderbook snapshot with bid/ask levels."""

    bids: list[tuple[float, float]]  # [(price, quantity), ...]
    asks: list[tuple[float, float]]  # [(price, quantity), ...]

    def __post_init__(self) -> None:
        """Validate orderbook structure."""
        if not self.bids:
            raise ValueError("Orderbook must have at least one bid")
        if not self.asks:
            raise ValueError("Orderbook must have at least one ask")

        # Bids should be descending (highest price first)
        bid_prices = [price for price, _ in self.bids]
        if bid_prices != sorted(bid_prices, reverse=True):
            raise ValueError("Bid prices must be in descending order")

        # Asks should be ascending (lowest price first)
        ask_prices = [price for price, _ in self.asks]
        if ask_prices != sorted(ask_prices):
            raise ValueError("Ask prices must be in ascending order")

    @property
    def best_bid(self) -> float:
        """Highest bid price."""
        return self.bids[0][0]

    @property
    def best_ask(self) -> float:
        """Lowest ask price."""
        return self.asks[0][0]

    @property
    def spread(self) -> float:
        """Bid-ask spread in price units."""
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> float:
        """Mid-market price."""
        return (self.best_bid + self.best_ask) / 2.0
