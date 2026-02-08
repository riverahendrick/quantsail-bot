"""Tests for HistoricalDataFetcher."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestHistoricalDataFetcher:
    """Test suite for HistoricalDataFetcher class."""

    @pytest.fixture
    def mock_ccxt(self):
        """Create a mock ccxt module."""
        with patch("quantsail_engine.research.data_fetcher.ccxt") as mock:
            mock_exchange = MagicMock()
            mock_exchange.rateLimit = 100
            mock.binance.return_value = mock_exchange
            yield mock, mock_exchange

    @pytest.fixture
    def fetcher(self, mock_ccxt):
        """Create a HistoricalDataFetcher with mocked ccxt."""
        from quantsail_engine.research.data_fetcher import HistoricalDataFetcher
        return HistoricalDataFetcher(exchange_id="binance")

    @pytest.fixture
    def sample_candles(self) -> list[list]:
        """Sample OHLCV candles for testing."""
        base_ts = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        return [
            [base_ts, 42000.0, 42500.0, 41800.0, 42200.0, 100.5],
            [base_ts + 60000, 42200.0, 42300.0, 42100.0, 42150.0, 80.2],
            [base_ts + 120000, 42150.0, 42400.0, 42100.0, 42350.0, 95.8],
        ]

    def test_init_success(self, mock_ccxt):
        """Test successful initialization."""
        from quantsail_engine.research.data_fetcher import HistoricalDataFetcher
        
        fetcher = HistoricalDataFetcher("binance")
        assert fetcher.exchange_id == "binance"
        # Exchange not yet accessed, should be None
        assert fetcher._exchange is None

    def test_init_no_ccxt(self):
        """Test initialization fails without ccxt."""
        with patch("quantsail_engine.research.data_fetcher.ccxt", None):
            from quantsail_engine.research import data_fetcher
            # Force reimport to get the error
            data_fetcher.ccxt = None
            
            with pytest.raises(ImportError, match="ccxt is required"):
                data_fetcher.HistoricalDataFetcher()

    def test_exchange_lazy_initialization(self, fetcher, mock_ccxt):
        """Test exchange is lazily initialized on first access."""
        mock, mock_exchange = mock_ccxt
        
        # Access exchange property
        exchange = fetcher.exchange
        
        # Should have created the exchange
        mock.binance.assert_called_once()
        assert exchange == mock_exchange

    def test_exchange_cached(self, fetcher, mock_ccxt):
        """Test exchange instance is cached."""
        mock, mock_exchange = mock_ccxt
        
        # Access multiple times
        _ = fetcher.exchange
        _ = fetcher.exchange
        
        # Should only create once
        assert mock.binance.call_count == 1

    def test_fetch_ohlcv_success(self, fetcher, mock_ccxt, sample_candles):
        """Test successful OHLCV fetch."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = sample_candles
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc)
        
        result = fetcher.fetch_ohlcv("BTC/USDT", "1m", since, until)
        
        assert len(result) == 3
        mock_exchange.fetch_ohlcv.assert_called()

    def test_fetch_ohlcv_naive_datetime_raises(self, fetcher):
        """Test naive datetime raises ValueError."""
        naive_dt = datetime(2024, 1, 1)  # No timezone
        
        with pytest.raises(ValueError, match="timezone-aware"):
            fetcher.fetch_ohlcv("BTC/USDT", "1m", naive_dt)

    def test_fetch_ohlcv_naive_until_raises(self, fetcher):
        """Test naive until datetime raises ValueError."""
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        naive_until = datetime(2024, 1, 2)
        
        with pytest.raises(ValueError, match="timezone-aware"):
            fetcher.fetch_ohlcv("BTC/USDT", "1m", since, naive_until)

    def test_fetch_ohlcv_default_until(self, fetcher, mock_ccxt, sample_candles):
        """Test until defaults to now if not specified."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = sample_candles
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        # until not specified
        
        result = fetcher.fetch_ohlcv("BTC/USDT", "1m", since)
        
        assert len(result) == 3

    def test_fetch_ohlcv_pagination(self, fetcher, mock_ccxt):
        """Test pagination when multiple batches needed."""
        _, mock_exchange = mock_ccxt
        
        # First batch - returns full limit, indicating more data
        base_ts = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        batch1 = [[base_ts + i * 60000, 42000, 42100, 41900, 42050, 50] for i in range(1000)]
        batch2 = [[base_ts + 1000 * 60000 + i * 60000, 42000, 42100, 41900, 42050, 50] for i in range(500)]
        
        mock_exchange.fetch_ohlcv.side_effect = [batch1, batch2]
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        result = fetcher.fetch_ohlcv("BTC/USDT", "1m", since, until)
        
        # Should have fetched 1500 total candles
        assert len(result) == 1500
        assert mock_exchange.fetch_ohlcv.call_count == 2

    def test_fetch_ohlcv_empty_response(self, fetcher, mock_ccxt):
        """Test handling empty response from exchange."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = []
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = fetcher.fetch_ohlcv("BTC/USDT", "1m", since)
        
        assert result == []

    def test_fetch_ohlcv_network_error_retry(self, fetcher, mock_ccxt, sample_candles):
        """Test network error triggers retry."""
        mock, mock_exchange = mock_ccxt
        
        # Create a mock network error
        network_error = MagicMock()
        network_error.__class__.__name__ = "NetworkError"
        mock.NetworkError = type("NetworkError", (Exception,), {})
        
        # First call raises network error, second succeeds
        mock_exchange.fetch_ohlcv.side_effect = [
            mock.NetworkError("Connection reset"),
            sample_candles,
        ]
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        with patch("time.sleep"):  # Don't actually sleep in tests
            result = fetcher.fetch_ohlcv("BTC/USDT", "1m", since)
        
        assert len(result) == 3
        assert mock_exchange.fetch_ohlcv.call_count == 2

    def test_fetch_ohlcv_exchange_error_raises(self, fetcher, mock_ccxt):
        """Test exchange error is re-raised."""
        mock, mock_exchange = mock_ccxt
        
        # Use generic Exception
        mock.ExchangeError = Exception
        mock_exchange.fetch_ohlcv.side_effect = Exception("Invalid symbol")
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        with pytest.raises(Exception):
            fetcher.fetch_ohlcv("INVALID/PAIR", "1m", since)

    def test_fetch_multiple_symbols(self, fetcher, mock_ccxt, sample_candles):
        """Test fetching multiple symbols."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = sample_candles
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        
        result = fetcher.fetch_multiple_symbols(symbols, "1m", since)
        
        assert len(result) == 3
        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert "SOL/USDT" in result
        assert len(result["BTC/USDT"]) == 3

    def test_save_csv(self, fetcher, sample_candles, tmp_path):
        """Test saving candles to CSV."""
        data = {"BTC/USDT": sample_candles}
        
        result = fetcher.save_csv(data, tmp_path, "1m")
        
        assert len(result) == 1
        filepath = result[0]
        assert filepath.exists()
        assert "BTC_USDT" in filepath.name
        assert "1m" in filepath.name
        assert filepath.suffix == ".csv"
        
        # Verify contents
        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert "open" in rows[0]
            assert "close" in rows[0]

    def test_save_csv_creates_directory(self, fetcher, sample_candles, tmp_path):
        """Test save_csv creates output directory if needed."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        data = {"ETH/USDT": sample_candles}
        
        result = fetcher.save_csv(data, new_dir)
        
        assert new_dir.exists()
        assert len(result) == 1

    def test_save_parquet_fallback(self, fetcher, sample_candles, tmp_path):
        """Test parquet falls back to CSV when pyarrow not available."""
        data = {"BTC/USDT": sample_candles}
        
        # Mock the import to raise ImportError in save_parquet
        import builtins
        original_import = builtins.__import__
        
        def import_mock(name, *args, **kwargs):
            if name == "pyarrow" or name.startswith("pyarrow."):
                raise ImportError("pyarrow not installed (mocked)")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, "__import__", side_effect=import_mock):
            result = fetcher.save_parquet(data, tmp_path, "5m")
        
        # Verify it saved as CSV (fallback)
        assert len(result) == 1
        assert result[0].suffix == ".csv"

    def test_save_parquet_success(self, fetcher, sample_candles, tmp_path):
        """Test saving candles to Parquet when pyarrow is available."""
        import pyarrow
        import pyarrow.parquet
        
        data = {"BTC/USDT": sample_candles}
        
        result = fetcher.save_parquet(data, tmp_path, "5m")
        
        # Should have created parquet file
        assert len(result) == 1
        filepath = result[0]
        assert filepath.exists()
        assert filepath.suffix == ".parquet"
        
        # Verify can read it back
        import pyarrow.parquet as pq
        table = pq.read_table(filepath)
        assert len(table) == len(sample_candles)


class TestHistoricalDataFetcherDataFrame:
    """Tests for DataFrame-related functionality."""

    @pytest.fixture
    def mock_ccxt(self):
        """Create a mock ccxt module."""
        with patch("quantsail_engine.research.data_fetcher.ccxt") as mock:
            mock_exchange = MagicMock()
            mock_exchange.rateLimit = 100
            mock.binance.return_value = mock_exchange
            yield mock, mock_exchange

    @pytest.fixture
    def mock_pandas(self):
        """Create mock pandas."""
        with patch("quantsail_engine.research.data_fetcher.pd") as mock:
            yield mock

    @pytest.fixture
    def sample_candles(self) -> list[list]:
        """Sample OHLCV candles."""
        base_ts = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        return [
            [base_ts, 42000.0, 42500.0, 41800.0, 42200.0, 100.5],
            [base_ts + 60000, 42200.0, 42300.0, 42100.0, 42150.0, 80.2],
        ]

    def test_fetch_ohlcv_df_no_pandas(self, mock_ccxt):
        """Test fetch_ohlcv_df raises without pandas."""
        from quantsail_engine.research.data_fetcher import HistoricalDataFetcher
        
        fetcher = HistoricalDataFetcher()
        
        with patch("quantsail_engine.research.data_fetcher.pd", None):
            from quantsail_engine.research import data_fetcher
            data_fetcher.pd = None
            
            # Access the fetcher method directly after patching
            since = datetime(2024, 1, 1, tzinfo=timezone.utc)
            
            with pytest.raises(ImportError, match="pandas is required"):
                fetcher.fetch_ohlcv_df("BTC/USDT", "1m", since)

    def test_fetch_ohlcv_df_success(self, mock_ccxt, sample_candles):
        """Test fetch_ohlcv_df with mocked pandas."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = sample_candles
        
        import pandas as pd
        from quantsail_engine.research.data_fetcher import HistoricalDataFetcher
        
        with patch("quantsail_engine.research.data_fetcher.pd", pd):
            fetcher = HistoricalDataFetcher()
            since = datetime(2024, 1, 1, tzinfo=timezone.utc)
            
            df = fetcher.fetch_ohlcv_df("BTC/USDT", "1m", since)
            
            assert len(df) == 2
            assert "open" in df.columns
            assert "close" in df.columns

    def test_fetch_ohlcv_df_empty(self, mock_ccxt):
        """Test fetch_ohlcv_df with empty result."""
        _, mock_exchange = mock_ccxt
        mock_exchange.fetch_ohlcv.return_value = []
        
        import pandas as pd
        from quantsail_engine.research.data_fetcher import HistoricalDataFetcher
        
        with patch("quantsail_engine.research.data_fetcher.pd", pd):
            fetcher = HistoricalDataFetcher()
            since = datetime(2024, 1, 1, tzinfo=timezone.utc)
            
            df = fetcher.fetch_ohlcv_df("BTC/USDT", "1m", since)
            
            assert len(df) == 0
            assert "open" in df.columns
