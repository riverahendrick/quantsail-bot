"""Historical data fetcher for backtesting and research.

This module provides a reusable HistoricalDataFetcher class that wraps
exchange APIs (via ccxt) to download OHLCV data with proper pagination,
rate limiting, and export capabilities.

Example:
    >>> fetcher = HistoricalDataFetcher()
    >>> since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    >>> df = fetcher.fetch_ohlcv("BTC/USDT", "5m", since)
    >>> fetcher.save_parquet({"BTC/USDT": df}, "./data")
"""

import csv
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import ccxt
except ImportError:
    ccxt = None  # type: ignore[assignment]

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Historical OHLCV data fetcher using ccxt.
    
    Fetches candlestick data from supported exchanges with automatic
    pagination, rate limiting, and error handling.
    
    Attributes:
        exchange_id: Exchange identifier (e.g., 'binance')
        exchange: Initialized ccxt exchange instance
    
    Example:
        >>> from datetime import datetime, timezone
        >>> fetcher = HistoricalDataFetcher(exchange_id="binance")
        >>> since = datetime(2024, 6, 1, tzinfo=timezone.utc)
        >>> df = fetcher.fetch_ohlcv("ETH/USDT", "1h", since)
        >>> print(f"Fetched {len(df)} candles")
    """
    
    def __init__(self, exchange_id: str = "binance") -> None:
        """Initialize the data fetcher.
        
        Args:
            exchange_id: Exchange to fetch from (default: binance)
            
        Raises:
            ImportError: If ccxt is not installed
        """
        if ccxt is None:
            raise ImportError(
                "ccxt is required for HistoricalDataFetcher. "
                "Install with: pip install ccxt"
            )
        
        self.exchange_id = exchange_id
        self._exchange: Any = None  # Lazy initialization
    
    @property
    def exchange(self) -> Any:
        """Get or create exchange instance (lazy initialization)."""
        if self._exchange is None:
            exchange_class = getattr(ccxt, self.exchange_id)
            self._exchange = exchange_class({
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
        return self._exchange
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime | None = None,
        limit_per_request: int = 1000,
    ) -> list[list]:
        """Fetch OHLCV data with automatic pagination.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle interval ('1m', '5m', '15m', '1h', '4h', '1d')
            since: Start datetime (must be timezone-aware)
            until: End datetime (default: now)
            limit_per_request: Max candles per request (default: 1000)
            
        Returns:
            List of OHLCV candles: [timestamp_ms, open, high, low, close, volume]
            
        Raises:
            ValueError: If since is naive datetime
            ccxt.ExchangeError: If API request fails
        """
        if since.tzinfo is None:
            raise ValueError("since must be timezone-aware datetime")
        
        if until is None:
            until = datetime.now(timezone.utc)
        elif until.tzinfo is None:
            raise ValueError("until must be timezone-aware datetime")
        
        since_ms = int(since.timestamp() * 1000)
        until_ms = int(until.timestamp() * 1000)
        
        all_candles: list[list] = []
        current_since = since_ms
        
        logger.info(f"Fetching {symbol} {timeframe} from {since.isoformat()}")
        
        while current_since < until_ms:
            try:
                candles = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_since,
                    limit=limit_per_request,
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                last_timestamp = candles[-1][0]
                
                # Move to next batch (add 1ms to avoid duplicates)
                current_since = last_timestamp + 1
                
                # Rate limit friendly
                if self.exchange.rateLimit:
                    time.sleep(self.exchange.rateLimit / 1000)
                
                # Stop if we've reached the end or got fewer than requested
                if len(candles) < limit_per_request:
                    break
                    
            except ccxt.NetworkError as e:
                logger.warning(f"Network error: {e}. Retrying in 5s...")
                time.sleep(5)
                continue
            except ccxt.ExchangeError:
                logger.error(f"Exchange error fetching {symbol}")
                raise
        
        logger.info(f"Fetched {len(all_candles)} candles for {symbol}")
        return all_candles
    
    def fetch_ohlcv_df(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime | None = None,
    ) -> "pd.DataFrame":
        """Fetch OHLCV data as a pandas DataFrame.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle interval
            since: Start datetime
            until: End datetime (default: now)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            Index is the timestamp column.
            
        Raises:
            ImportError: If pandas is not installed
        """
        if pd is None:
            raise ImportError(
                "pandas is required for fetch_ohlcv_df. "
                "Install with: pip install pandas"
            )
        
        candles = self.fetch_ohlcv(symbol, timeframe, since, until)
        
        if not candles:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            ).set_index("timestamp")
        
        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        
        if until is not None:
            df = df[(df["timestamp"] >= since) & (df["timestamp"] <= until)]
        
        return df.set_index("timestamp")
    
    def fetch_multiple_symbols(
        self,
        symbols: list[str],
        timeframe: str,
        since: datetime,
        until: datetime | None = None,
    ) -> dict[str, list[list]]:
        """Fetch OHLCV data for multiple symbols.
        
        Args:
            symbols: List of trading pairs
            timeframe: Candle interval
            since: Start datetime
            until: End datetime (default: now)
            
        Returns:
            Dict mapping symbol -> list of candles
        """
        data: dict[str, list[list]] = {}
        
        for symbol in symbols:
            logger.info(f"Fetching {symbol}...")
            candles = self.fetch_ohlcv(symbol, timeframe, since, until)
            data[symbol] = candles
            logger.info(f"  {len(candles)} candles fetched")
        
        return data
    
    def save_csv(
        self,
        data: dict[str, list[list]],
        output_dir: str | Path,
        timeframe: str = "",
    ) -> list[Path]:
        """Save candles to CSV files.
        
        Args:
            data: Dict mapping symbol -> candles
            output_dir: Output directory
            timeframe: Timeframe for filename (optional)
            
        Returns:
            List of paths to saved files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files: list[Path] = []
        
        for symbol, candles in data.items():
            safe_symbol = symbol.replace("/", "_")
            suffix = f"_{timeframe}" if timeframe else ""
            filename = f"{safe_symbol}{suffix}_ohlcv.csv"
            filepath = output_path / filename
            
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
                for candle in candles:
                    writer.writerow([
                        datetime.fromtimestamp(
                            candle[0] / 1000, tz=timezone.utc
                        ).isoformat(),
                        candle[1],
                        candle[2],
                        candle[3],
                        candle[4],
                        candle[5],
                    ])
            
            logger.info(f"Saved {len(candles)} candles to {filepath}")
            saved_files.append(filepath)
        
        return saved_files
    
    def save_parquet(
        self,
        data: dict[str, list[list]],
        output_dir: str | Path,
        timeframe: str = "",
    ) -> list[Path]:
        """Save candles to Parquet files for faster loading.
        
        Args:
            data: Dict mapping symbol -> candles
            output_dir: Output directory
            timeframe: Timeframe for filename (optional)
            
        Returns:
            List of paths to saved files
            
        Raises:
            ImportError: If pyarrow is not installed
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            logger.warning("pyarrow not installed; falling back to CSV")
            return self.save_csv(data, output_dir, timeframe)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files: list[Path] = []
        
        for symbol, candles in data.items():
            safe_symbol = symbol.replace("/", "_")
            suffix = f"_{timeframe}" if timeframe else ""
            filename = f"{safe_symbol}{suffix}_ohlcv.parquet"
            filepath = output_path / filename
            
            timestamps = [
                datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
                for c in candles
            ]
            
            table = pa.table({
                "timestamp": timestamps,
                "open": [c[1] for c in candles],
                "high": [c[2] for c in candles],
                "low": [c[3] for c in candles],
                "close": [c[4] for c in candles],
                "volume": [c[5] for c in candles],
            })
            
            pq.write_table(table, filepath)
            logger.info(f"Saved {len(candles)} candles to {filepath}")
            saved_files.append(filepath)
        
        return saved_files
