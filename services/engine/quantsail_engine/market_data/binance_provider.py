"""Binance Spot market data provider using CCXT.

Provides real-time candles and orderbook data via the Binance REST API.
Uses CCXT's built-in rate limiting with exponential backoff for resilience.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.candle import Candle, Orderbook

logger = logging.getLogger(__name__)

# Default maximum age for the most recent candle (seconds).
_DEFAULT_MAX_CANDLE_AGE_SECONDS = 600  # 10 minutes


class BinanceMarketDataProvider(MarketDataProvider):
    """Real Binance market data provider via CCXT.

    Attributes:
        exchange: CCXT exchange instance (must have ``enableRateLimit=True``).
        max_candle_age_seconds: Reject candles older than this threshold.
        max_retries: Maximum retry attempts on transient failures.
        base_backoff_seconds: Initial backoff interval for retries.
    """

    def __init__(
        self,
        exchange: Any,
        *,
        max_candle_age_seconds: int = _DEFAULT_MAX_CANDLE_AGE_SECONDS,
        max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
    ) -> None:
        """Initialise the provider.

        Args:
            exchange: A configured CCXT exchange instance.
            max_candle_age_seconds: Maximum age in seconds for the latest candle.
            max_retries: Number of retry attempts on transient errors.
            base_backoff_seconds: Base interval for exponential backoff.
        """
        self.exchange = exchange
        self.max_candle_age_seconds = max_candle_age_seconds
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds

    # -- Public interface (MarketDataProvider) ---------------------------------

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Fetch OHLCV candles from Binance.

        Args:
            symbol: Trading pair (e.g. ``"BTC/USDT"``).
            timeframe: Candle timeframe (e.g. ``"1m"``, ``"5m"``, ``"1h"``).
            limit: Number of candles to fetch.

        Returns:
            List of ``Candle`` objects, oldest first.

        Raises:
            RuntimeError: If all retry attempts fail or data is stale.
        """
        raw = self._retry(
            lambda: self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit),
            context=f"fetch_ohlcv({symbol}, {timeframe})",
        )

        if not raw:
            raise RuntimeError(
                f"Binance returned empty candle data for {symbol}/{timeframe}"
            )

        candles = self._convert_candles(raw)
        self._check_staleness(candles, symbol, timeframe)
        return candles

    def get_orderbook(self, symbol: str, depth_levels: int) -> Orderbook:
        """Fetch an orderbook snapshot from Binance.

        Args:
            symbol: Trading pair (e.g. ``"BTC/USDT"``).
            depth_levels: Number of price levels per side.

        Returns:
            ``Orderbook`` dataclass instance.

        Raises:
            RuntimeError: If all retry attempts fail or orderbook is empty.
        """
        raw = self._retry(
            lambda: self.exchange.fetch_order_book(symbol, limit=depth_levels),
            context=f"fetch_order_book({symbol})",
        )

        if not raw or not raw.get("bids") or not raw.get("asks"):
            raise RuntimeError(
                f"Binance returned empty orderbook for {symbol}"
            )

        return self._convert_orderbook(raw, depth_levels)

    # -- Internal helpers ------------------------------------------------------

    def _retry(self, fn: Any, *, context: str) -> Any:
        """Execute ``fn`` with exponential backoff.

        Args:
            fn: Callable to execute.
            context: Human-readable label for log messages.

        Returns:
            Return value of ``fn``.

        Raises:
            RuntimeError: After exhausting all retries.
        """
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                wait = self.base_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Binance API error on %s (attempt %d/%d): %s — retrying in %.1fs",
                    context,
                    attempt,
                    self.max_retries,
                    exc,
                    wait,
                )
                if attempt < self.max_retries:
                    time.sleep(wait)

        raise RuntimeError(
            f"Binance API failed after {self.max_retries} retries "
            f"({context}): {last_error}"
        )

    @staticmethod
    def _convert_candles(raw: list[list[Any]]) -> list[Candle]:
        """Convert raw CCXT OHLCV arrays to ``Candle`` objects.

        Args:
            raw: List of ``[timestamp_ms, open, high, low, close, volume]``.

        Returns:
            List of ``Candle`` dataclass instances.
        """
        candles: list[Candle] = []
        for row in raw:
            ts_ms, o, h, l, c, v = row[0], row[1], row[2], row[3], row[4], row[5]
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc),
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                )
            )
        return candles

    def _check_staleness(
        self, candles: list[Candle], symbol: str, timeframe: str
    ) -> None:
        """Raise if the newest candle is older than the configured threshold.

        Args:
            candles: List of candles (oldest first).
            symbol: Symbol for error messages.
            timeframe: Timeframe for error messages.

        Raises:
            RuntimeError: If data is stale.
        """
        if not candles:
            return

        newest = candles[-1]
        age_seconds = (
            datetime.now(timezone.utc) - newest.timestamp
        ).total_seconds()

        if age_seconds > self.max_candle_age_seconds:
            raise RuntimeError(
                f"Stale market data for {symbol}/{timeframe}: "
                f"newest candle is {age_seconds:.0f}s old "
                f"(max {self.max_candle_age_seconds}s)"
            )

    @staticmethod
    def _convert_orderbook(raw: dict[str, Any], depth: int) -> Orderbook:
        """Convert a CCXT orderbook dict to an ``Orderbook`` dataclass.

        Args:
            raw: CCXT orderbook dict with ``bids`` and ``asks`` lists.
            depth: Maximum number of levels per side.

        Returns:
            ``Orderbook`` instance with properly sorted levels.
        """
        bids_raw = raw.get("bids", [])[:depth]
        asks_raw = raw.get("asks", [])[:depth]

        # CCXT returns bids descending, asks ascending — which matches Orderbook
        bids = [(float(price), float(qty)) for price, qty in bids_raw]
        asks = [(float(price), float(qty)) for price, qty in asks_raw]

        return Orderbook(bids=bids, asks=asks)
