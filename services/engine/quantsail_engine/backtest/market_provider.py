"""Backtest market data provider using historical OHLCV data."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.candle import Candle, Orderbook


class BacktestMarketProvider(MarketDataProvider):
    """Market data provider for backtesting using historical data.

    This provider reads historical OHLCV data from CSV or Parquet files
    and yields candles based on the simulated time from TimeManager.

    Example:
        >>> time_mgr = TimeManager()
        >>> provider = BacktestMarketProvider(
        ...     data_file="BTC_USDT_1m.csv",
        ...     time_manager=time_mgr,
        ...     symbol="BTC/USDT"
        ... )
        >>> time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        >>> candles = provider.get_candles("BTC/USDT", "1m", 100)
    """

    def __init__(
        self,
        data_file: str | Path,
        time_manager: TimeManager,
        symbol: str,
    ):
        """Initialize backtest market provider.

        Args:
            data_file: Path to OHLCV data file (CSV or Parquet)
            time_manager: Time manager for simulated time
            symbol: Trading pair symbol (e.g., "BTC/USDT")
        """
        self.data_file = Path(data_file)
        self.time_manager = time_manager
        self.symbol = symbol
        self._candles: list[Candle] = []
        self._candles_by_time: dict[int, Candle] = {}
        self._timestamps: list[int] = []

        self._load_data()

    def _load_data(self) -> None:
        """Load historical data from file."""
        if not self.data_file.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_file}")

        if self.data_file.suffix.lower() == ".csv":
            self._load_csv()
        elif self.data_file.suffix.lower() == ".parquet":
            self._load_parquet()
        else:
            raise ValueError(f"Unsupported file format: {self.data_file.suffix}")

        # Build timestamp index for fast lookup
        self._timestamps = sorted(self._candles_by_time.keys())

        if not self._candles:
            raise ValueError(f"No candles loaded from {self.data_file}")

        print(f"📊 Loaded {len(self._candles)} candles from {self.data_file.name}")
        print(f"   Period: {self._candles[0].timestamp} to {self._candles[-1].timestamp}")

    def _load_csv(self) -> None:
        """Load candles from CSV file."""
        with open(self.data_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse timestamp (ISO format)
                ts_str = row['timestamp']
                timestamp = datetime.fromisoformat(ts_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                candle = Candle(
                    timestamp=timestamp,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume']),
                )
                self._candles.append(candle)
                self._candles_by_time[int(timestamp.timestamp())] = candle

    def _load_parquet(self) -> None:
        """Load candles from Parquet file."""
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError("pyarrow required for Parquet support. Install with: pip install pyarrow")

        table = pq.read_table(self.data_file)
        
        timestamps = table['timestamp'].to_pylist()
        opens = table['open'].to_pylist()
        highs = table['high'].to_pylist()
        lows = table['low'].to_pylist()
        closes = table['close'].to_pylist()
        volumes = table['volume'].to_pylist()

        for i in range(len(timestamps)):
            timestamp = timestamps[i]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            candle = Candle(
                timestamp=timestamp,
                open=opens[i],
                high=highs[i],
                low=lows[i],
                close=closes[i],
                volume=volumes[i],
            )
            self._candles.append(candle)
            self._candles_by_time[int(timestamp.timestamp())] = candle

    def _get_current_candle(self) -> Candle | None:
        """Get the candle at or before the current simulated time.

        Returns:
            Most recent candle available at current simulated time
        """
        current_time = self.time_manager.now()
        current_ts = int(current_time.timestamp())

        # Find the most recent candle at or before current time
        # Use binary search for efficiency
        left, right = 0, len(self._timestamps) - 1
        result_idx = -1

        while left <= right:
            mid = (left + right) // 2
            if self._timestamps[mid] <= current_ts:
                result_idx = mid
                left = mid + 1
            else:
                right = mid - 1

        if result_idx >= 0:
            ts = self._timestamps[result_idx]
            return self._candles_by_time[ts]
        return None

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Fetch OHLCV candles up to the current simulated time.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Candle timeframe (e.g., "1m", "5m", "1h")
            limit: Number of candles to fetch

        Returns:
            List of candles, most recent last (only up to current simulated time)

        Raises:
            ValueError: If symbol doesn't match or no candles available
        """
        if symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: {symbol} != {self.symbol}")

        current_candle = self._get_current_candle()
        if current_candle is None:
            return []

        current_ts = int(current_candle.timestamp.timestamp())

        # Find index of current candle
        current_idx = self._timestamps.index(current_ts)

        # Return up to 'limit' candles ending at current position
        start_idx = max(0, current_idx - limit + 1)
        selected_timestamps = self._timestamps[start_idx:current_idx + 1]

        return [self._candles_by_time[ts] for ts in selected_timestamps]

    def get_orderbook(self, symbol: str, depth_levels: int) -> Orderbook:
        """Generate a simulated orderbook based on current candle.

        Creates a synthetic orderbook around the current close price
        with realistic bid/ask spread.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            depth_levels: Number of price levels to fetch per side

        Returns:
            Synthetic orderbook with bids and asks

        Raises:
            ValueError: If no current candle available
        """
        if symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: {symbol} != {self.symbol}")

        candle = self._get_current_candle()
        if candle is None:
            raise ValueError("No candle available at current simulated time")

        # Use close price as mid price
        mid_price = candle.close

        # Generate synthetic spread (0.01% to 0.05% based on volatility)
        volatility = (candle.high - candle.low) / candle.close
        spread_pct = max(0.0001, min(0.0005, volatility * 0.1))
        half_spread = mid_price * spread_pct / 2

        best_bid = mid_price - half_spread
        best_ask = mid_price + half_spread

        # Generate orderbook depth
        bids: list[tuple[float, float]] = []
        asks: list[tuple[float, float]] = []

        # Base quantity that decreases with depth
        base_qty = 1.0

        for i in range(depth_levels):
            # Price levels get progressively further from mid
            depth_factor = 1 + (i * 0.001)  # 0.1% increments

            bid_price = best_bid * (1 - i * 0.0005)  # Bids below best bid
            ask_price = best_ask * (1 + i * 0.0005)  # Asks above best ask

            # Quantity decreases with depth
            qty = base_qty / (i + 1)

            bids.append((round(bid_price, 2), round(qty, 4)))
            asks.append((round(ask_price, 2), round(qty, 4)))

        return Orderbook(bids=bids, asks=asks)

    def get_data_range(self) -> tuple[datetime, datetime]:
        """Get the available data time range.

        Returns:
            Tuple of (start_time, end_time)
        """
        if not self._candles:
            raise ValueError("No data loaded")
        return (self._candles[0].timestamp, self._candles[-1].timestamp)

    def iter_timestamps(
        self,
        interval_seconds: int = 300,  # 5 minutes default
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterator[datetime]:
        """Iterate through all available timestamps at given intervals.

        Args:
            interval_seconds: Interval between simulation steps
            start_time: Optional start time to begin iteration
            end_time: Optional end time to stop iteration

        Yields:
            Timestamps for each simulation step
        """
        if not self._candles:
            raise ValueError("No data loaded")

        data_start = self._candles[0].timestamp
        data_end = self._candles[-1].timestamp

        # Use provided bounds or default to data range
        current = start_time if start_time else data_start
        stop_time = end_time if end_time else data_end

        # Ensure we don't go outside data range
        current = max(current, data_start)
        stop_time = min(stop_time, data_end)

        while current <= stop_time:
            yield current
            current = datetime.fromtimestamp(
                current.timestamp() + interval_seconds,
                tz=timezone.utc,
            )
