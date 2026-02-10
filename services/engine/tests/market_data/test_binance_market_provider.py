"""Tests for BinanceMarketDataProvider."""

import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from quantsail_engine.market_data.binance_provider import BinanceMarketDataProvider
from quantsail_engine.models.candle import Candle, Orderbook


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_raw_ohlcv(
    count: int = 5, base_ts_ms: int | None = None
) -> list[list[Any]]:
    """Return raw CCXT OHLCV rows with timestamps close to *now*."""
    if base_ts_ms is None:
        base_ts_ms = int(time.time() * 1000) - (count * 60_000)
    rows: list[list[Any]] = []
    for i in range(count):
        ts = base_ts_ms + i * 60_000
        rows.append([ts, 100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i, 1000.0 + i])
    return rows


def _make_raw_orderbook() -> dict[str, Any]:
    """Return a CCXT orderbook dict."""
    return {
        "bids": [[100.0, 1.5], [99.5, 2.0], [99.0, 3.0]],
        "asks": [[100.5, 1.0], [101.0, 2.5], [101.5, 4.0]],
    }


def _mock_exchange(
    ohlcv: list[list[Any]] | None = None,
    orderbook: dict[str, Any] | None = None,
) -> MagicMock:
    """Return a MagicMock exchange that behaves like a CCXT instance."""
    exchange = MagicMock()
    exchange.fetch_ohlcv.return_value = ohlcv if ohlcv is not None else _make_raw_ohlcv()
    exchange.fetch_order_book.return_value = (
        orderbook if orderbook is not None else _make_raw_orderbook()
    )
    return exchange


# ---------------------------------------------------------------------------
# get_candles tests
# ---------------------------------------------------------------------------


class TestGetCandles:
    """Tests for BinanceMarketDataProvider.get_candles."""

    def test_happy_path_returns_candles(self) -> None:
        raw = _make_raw_ohlcv(3)
        exchange = _mock_exchange(ohlcv=raw)
        provider = BinanceMarketDataProvider(exchange)

        candles = provider.get_candles("BTC/USDT", "5m", 3)

        assert len(candles) == 3
        assert all(isinstance(c, Candle) for c in candles)
        exchange.fetch_ohlcv.assert_called_once_with("BTC/USDT", "5m", limit=3)

    def test_candle_values_correct(self) -> None:
        ts_ms = int(time.time() * 1000) - 60_000
        raw = [[ts_ms, 100.0, 105.0, 99.0, 102.0, 5000.0]]
        exchange = _mock_exchange(ohlcv=raw)
        provider = BinanceMarketDataProvider(exchange)

        candles = provider.get_candles("ETH/USDT", "1m", 1)

        c = candles[0]
        assert c.open == 100.0
        assert c.high == 105.0
        assert c.low == 99.0
        assert c.close == 102.0
        assert c.volume == 5000.0
        assert c.timestamp.tzinfo == timezone.utc

    def test_empty_response_raises(self) -> None:
        exchange = _mock_exchange(ohlcv=[])
        provider = BinanceMarketDataProvider(exchange)

        with pytest.raises(RuntimeError, match="empty candle data"):
            provider.get_candles("BTC/USDT", "5m", 10)

    def test_stale_data_raises(self) -> None:
        old_ts_ms = int(time.time() * 1000) - 2_000_000  # ~33 min ago
        raw = [[old_ts_ms, 100.0, 105.0, 99.0, 102.0, 1000.0]]
        exchange = _mock_exchange(ohlcv=raw)
        provider = BinanceMarketDataProvider(exchange, max_candle_age_seconds=60)

        with pytest.raises(RuntimeError, match="Stale market data"):
            provider.get_candles("BTC/USDT", "5m", 1)

    def test_stale_data_passes_when_within_threshold(self) -> None:
        recent_ts_ms = int(time.time() * 1000) - 5_000  # 5s ago
        raw = [[recent_ts_ms, 100.0, 105.0, 99.0, 102.0, 1000.0]]
        exchange = _mock_exchange(ohlcv=raw)
        provider = BinanceMarketDataProvider(exchange, max_candle_age_seconds=600)

        candles = provider.get_candles("BTC/USDT", "5m", 1)
        assert len(candles) == 1

    def test_ccxt_exception_retries_and_raises(self) -> None:
        exchange = MagicMock()
        exchange.fetch_ohlcv.side_effect = Exception("Network error")
        provider = BinanceMarketDataProvider(
            exchange, max_retries=2, base_backoff_seconds=0.01
        )

        with pytest.raises(RuntimeError, match="failed after 2 retries"):
            provider.get_candles("BTC/USDT", "5m", 10)

        assert exchange.fetch_ohlcv.call_count == 2

    def test_ccxt_transient_then_success(self) -> None:
        raw = _make_raw_ohlcv(2)
        exchange = MagicMock()
        exchange.fetch_ohlcv.side_effect = [Exception("Timeout"), raw]
        provider = BinanceMarketDataProvider(
            exchange, max_retries=3, base_backoff_seconds=0.01
        )

        candles = provider.get_candles("BTC/USDT", "5m", 2)
        assert len(candles) == 2
        assert exchange.fetch_ohlcv.call_count == 2


# ---------------------------------------------------------------------------
# get_orderbook tests
# ---------------------------------------------------------------------------


class TestGetOrderbook:
    """Tests for BinanceMarketDataProvider.get_orderbook."""

    def test_happy_path_returns_orderbook(self) -> None:
        exchange = _mock_exchange()
        provider = BinanceMarketDataProvider(exchange)

        ob = provider.get_orderbook("BTC/USDT", 3)

        assert isinstance(ob, Orderbook)
        assert len(ob.bids) == 3
        assert len(ob.asks) == 3
        exchange.fetch_order_book.assert_called_once_with("BTC/USDT", limit=3)

    def test_orderbook_values_correct(self) -> None:
        exchange = _mock_exchange()
        provider = BinanceMarketDataProvider(exchange)

        ob = provider.get_orderbook("ETH/USDT", 3)

        assert ob.best_bid == 100.0
        assert ob.best_ask == 100.5
        assert ob.spread == pytest.approx(0.5)

    def test_depth_truncation(self) -> None:
        raw_ob = {
            "bids": [[100.0, 1.0], [99.5, 2.0], [99.0, 3.0], [98.5, 4.0]],
            "asks": [[100.5, 1.0], [101.0, 2.0], [101.5, 3.0], [102.0, 4.0]],
        }
        exchange = _mock_exchange(orderbook=raw_ob)
        provider = BinanceMarketDataProvider(exchange)

        ob = provider.get_orderbook("BTC/USDT", 2)
        assert len(ob.bids) == 2
        assert len(ob.asks) == 2

    def test_empty_bids_raises(self) -> None:
        raw_ob = {"bids": [], "asks": [[100.5, 1.0]]}
        exchange = _mock_exchange(orderbook=raw_ob)
        provider = BinanceMarketDataProvider(exchange)

        with pytest.raises(RuntimeError, match="empty orderbook"):
            provider.get_orderbook("BTC/USDT", 5)

    def test_empty_asks_raises(self) -> None:
        raw_ob = {"bids": [[100.0, 1.0]], "asks": []}
        exchange = _mock_exchange(orderbook=raw_ob)
        provider = BinanceMarketDataProvider(exchange)

        with pytest.raises(RuntimeError, match="empty orderbook"):
            provider.get_orderbook("BTC/USDT", 5)

    def test_none_response_raises(self) -> None:
        exchange = MagicMock()
        exchange.fetch_order_book.return_value = None
        provider = BinanceMarketDataProvider(
            exchange, max_retries=1, base_backoff_seconds=0.01
        )

        with pytest.raises(RuntimeError, match="empty orderbook"):
            provider.get_orderbook("BTC/USDT", 5)

    def test_ccxt_exception_retries_and_raises(self) -> None:
        exchange = MagicMock()
        exchange.fetch_order_book.side_effect = Exception("Rate limit")
        provider = BinanceMarketDataProvider(
            exchange, max_retries=2, base_backoff_seconds=0.01
        )

        with pytest.raises(RuntimeError, match="failed after 2 retries"):
            provider.get_orderbook("BTC/USDT", 5)

        assert exchange.fetch_order_book.call_count == 2


# ---------------------------------------------------------------------------
# Retry mechanism tests
# ---------------------------------------------------------------------------


class TestRetryMechanism:
    """Tests for _retry internal method."""

    def test_retry_succeeds_on_first(self) -> None:
        exchange = _mock_exchange()
        provider = BinanceMarketDataProvider(exchange, max_retries=3)

        result = provider._retry(lambda: 42, context="test")
        assert result == 42

    def test_retry_exponential_backoff_timing(self) -> None:
        exchange = MagicMock()
        call_count = 0

        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise Exception(f"fail #{call_count}")

        provider = BinanceMarketDataProvider(
            exchange, max_retries=3, base_backoff_seconds=0.01
        )

        with patch("quantsail_engine.market_data.binance_provider.time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError, match="failed after 3 retries"):
                provider._retry(always_fail, context="test")

            # Should have slept between attempts (not after last)
            assert mock_sleep.call_count == 2
            # First sleep: 0.01 * 2^0 = 0.01
            assert mock_sleep.call_args_list[0][0][0] == pytest.approx(0.01)
            # Second sleep: 0.01 * 2^1 = 0.02
            assert mock_sleep.call_args_list[1][0][0] == pytest.approx(0.02)


# ---------------------------------------------------------------------------
# Static helper tests
# ---------------------------------------------------------------------------


class TestConvertHelpers:
    """Tests for static conversion methods."""

    def test_convert_candles_preserves_order(self) -> None:
        raw = _make_raw_ohlcv(5)
        candles = BinanceMarketDataProvider._convert_candles(raw)

        assert len(candles) == 5
        # Timestamps should be ascending (oldest first)
        for i in range(1, len(candles)):
            assert candles[i].timestamp > candles[i - 1].timestamp

    def test_convert_orderbook_structure(self) -> None:
        raw = _make_raw_orderbook()
        ob = BinanceMarketDataProvider._convert_orderbook(raw, 3)

        assert isinstance(ob, Orderbook)
        # Bids descending
        assert ob.bids[0][0] > ob.bids[1][0]
        # Asks ascending
        assert ob.asks[0][0] < ob.asks[1][0]

    def test_check_staleness_empty_candles_no_error(self) -> None:
        exchange = _mock_exchange()
        provider = BinanceMarketDataProvider(exchange, max_candle_age_seconds=10)
        # Should not raise for empty list
        provider._check_staleness([], "BTC/USDT", "5m")
