"""Tests for BacktestMarketProvider."""

import csv
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from quantsail_engine.backtest.market_provider import BacktestMarketProvider
from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.models.candle import Candle


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    """Create a sample CSV file with OHLCV data."""
    csv_file = tmp_path / "test_data.csv"

    # Generate 100 minutes of data
    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    base_price = 50000.0

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        for i in range(100):
            ts = base_time + timedelta(minutes=i)
            price = base_price + (i * 10)  # Rising prices
            writer.writerow([
                ts.isoformat(),
                price,
                price + 5,
                price - 5,
                price + 2,
                1.5,
            ])

    return csv_file


class TestBacktestMarketProvider:
    """Test suite for BacktestMarketProvider."""

    def test_load_csv_data(self, sample_csv_file: Path) -> None:
        """Test loading data from CSV file."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        assert len(provider._candles) == 100
        assert provider._candles[0].timestamp == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    def test_get_candles_at_time(self, sample_csv_file: Path) -> None:
        """Test getting candles at specific simulated time."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        candles = provider.get_candles("BTC/USDT", "1m", 10)

        assert len(candles) == 10
        # Should return candles from 12:21 to 12:30 (10 candles)
        assert candles[0].timestamp == datetime(2024, 1, 1, 12, 21, tzinfo=timezone.utc)
        assert candles[-1].timestamp == datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

    def test_get_candles_advances_time(self, sample_csv_file: Path) -> None:
        """Test that candles returned are limited by current time."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        candles = provider.get_candles("BTC/USDT", "1m", 100)

        # Should only return 11 candles (12:00 to 12:10 inclusive)
        assert len(candles) == 11

    def test_get_orderbook(self, sample_csv_file: Path) -> None:
        """Test generating synthetic orderbook."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        orderbook = provider.get_orderbook("BTC/USDT", depth_levels=5)

        assert len(orderbook.bids) == 5
        assert len(orderbook.asks) == 5
        assert orderbook.best_bid < orderbook.best_ask
        assert orderbook.mid_price > 0

    def test_symbol_mismatch_raises(self, sample_csv_file: Path) -> None:
        """Test that wrong symbol raises ValueError."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        with pytest.raises(ValueError, match="Symbol mismatch"):
            provider.get_candles("ETH/USDT", "1m", 10)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that missing file raises FileNotFoundError."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        with pytest.raises(FileNotFoundError):
            BacktestMarketProvider(
                data_file=tmp_path / "nonexistent.csv",
                time_manager=time_mgr,
                symbol="BTC/USDT",
            )

    def test_get_data_range(self, sample_csv_file: Path) -> None:
        """Test getting data time range."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        start, end = provider.get_data_range()

        assert start == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert end == datetime(2024, 1, 1, 13, 39, tzinfo=timezone.utc)

    def test_iter_timestamps(self, sample_csv_file: Path) -> None:
        """Test timestamp iteration."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        timestamps = list(provider.iter_timestamps(interval_seconds=600))  # 10 min intervals

        # 100 minutes / 10 minute intervals = 10 timestamps
        assert len(timestamps) == 10
        assert timestamps[0] == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert timestamps[1] == datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc)


class TestBacktestMarketProviderNoLookAhead:
    """Tests to verify no look-ahead bias in data access."""

    def test_candles_do_not_exceed_current_time(self, sample_csv_file: Path) -> None:
        """Critical test: ensure no future data is accessible."""
        time_mgr = TimeManager()
        # Set time to 12:30 exactly
        current_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)
        time_mgr.set_time(current_time)

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        # Try to get 100 candles
        candles = provider.get_candles("BTC/USDT", "1m", 100)

        # Should only get candles up to current time (31 candles from 12:00 to 12:30)
        assert len(candles) == 31
        assert candles[-1].timestamp <= current_time

        # Advance time
        time_mgr.set_time(datetime(2024, 1, 1, 12, 40, tzinfo=timezone.utc))

        candles = provider.get_candles("BTC/USDT", "1m", 100)
        # Now should have 41 candles
        assert len(candles) == 41


class TestBacktestMarketProviderEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unsupported_file_format(self, tmp_path: Path) -> None:
        """Test that unsupported file format raises ValueError."""
        # Create a file with unsupported extension
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("some data")

        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        with pytest.raises(ValueError, match="Unsupported file format"):
            BacktestMarketProvider(
                data_file=txt_file,
                time_manager=time_mgr,
                symbol="BTC/USDT",
            )

    def test_get_candles_before_data_start(self, sample_csv_file: Path) -> None:
        """Test getting candles when time is before any data."""
        time_mgr = TimeManager()
        # Set time before any data exists
        time_mgr.set_time(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        candles = provider.get_candles("BTC/USDT", "1m", 10)
        assert candles == []  # No candles available yet

    def test_get_orderbook_symbol_mismatch(self, sample_csv_file: Path) -> None:
        """Test orderbook with wrong symbol raises ValueError."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        with pytest.raises(ValueError, match="Symbol mismatch"):
            provider.get_orderbook("ETH/USDT", depth_levels=5)

    def test_get_orderbook_before_data_start(self, sample_csv_file: Path) -> None:
        """Test orderbook raises when no candle available."""
        time_mgr = TimeManager()
        # Set time before any data exists
        time_mgr.set_time(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=sample_csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        with pytest.raises(ValueError, match="No candle available"):
            provider.get_orderbook("BTC/USDT", depth_levels=5)


class TestBacktestMarketProviderParquet:
    """Tests for Parquet file loading."""

    def test_load_parquet_data(self, tmp_path: Path) -> None:
        """Test loading data from Parquet file."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Create a sample parquet file
        parquet_file = tmp_path / "test_data.parquet"
        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        timestamps = [base_time + timedelta(minutes=i) for i in range(50)]
        opens = [50000.0 + i * 10 for i in range(50)]
        highs = [o + 5 for o in opens]
        lows = [o - 5 for o in opens]
        closes = [o + 2 for o in opens]
        volumes = [1.5] * 50

        table = pa.table({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
        })
        pq.write_table(table, parquet_file)

        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=parquet_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        assert len(provider._candles) == 50
        candles = provider.get_candles("BTC/USDT", "1m", 10)
        assert len(candles) == 10

    def test_load_parquet_with_string_timestamps(self, tmp_path: Path) -> None:
        """Test loading Parquet with ISO string timestamps."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet_file = tmp_path / "test_data.parquet"
        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Use string timestamps instead of datetime objects
        timestamps = [(base_time + timedelta(minutes=i)).isoformat() for i in range(20)]
        opens = [50000.0 + i * 10 for i in range(20)]
        highs = [o + 5 for o in opens]
        lows = [o - 5 for o in opens]
        closes = [o + 2 for o in opens]
        volumes = [1.5] * 20

        table = pa.table({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
        })
        pq.write_table(table, parquet_file)

        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=parquet_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        assert len(provider._candles) == 20
        candles = provider.get_candles("BTC/USDT", "1m", 5)
        assert len(candles) == 5


class TestBacktestMarketProviderEmptyData:
    """Tests for empty data handling."""

    def test_empty_csv_file_raises(self, tmp_path: Path) -> None:
        """Test that CSV with no data rows raises ValueError."""
        csv_file = tmp_path / "empty.csv"
        
        # Write only header, no data
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        with pytest.raises(ValueError, match="No candles loaded"):
            BacktestMarketProvider(
                data_file=csv_file,
                time_manager=time_mgr,
                symbol="BTC/USDT",
            )

    def test_naive_timestamp_csv(self, tmp_path: Path) -> None:
        """Test loading CSV with naive (no timezone) timestamps."""
        csv_file = tmp_path / "naive_timestamps.csv"
        base_time = datetime(2024, 1, 1, 12, 0)  # No timezone

        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            for i in range(10):
                ts = base_time + timedelta(minutes=i)
                writer.writerow([
                    ts.isoformat(),
                    50000 + i,
                    50010 + i,
                    49990 + i,
                    50005 + i,
                    1.0,
                ])

        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 5, tzinfo=timezone.utc))

        provider = BacktestMarketProvider(
            data_file=csv_file,
            time_manager=time_mgr,
            symbol="BTC/USDT",
        )

        assert len(provider._candles) == 10
        # Verify timezone was added
        assert provider._candles[0].timestamp.tzinfo == timezone.utc
