"""Unit tests for StubMarketDataProvider."""

from datetime import datetime, timezone

from quantsail_engine.market_data.stub_provider import StubMarketDataProvider


def test_stub_provider_default_init() -> None:
    """Test stub provider initializes with defaults."""
    provider = StubMarketDataProvider()
    assert provider.base_price == 50000.0
    assert provider.spread_bps == 2.0
    assert provider.volume == 100.0


def test_stub_provider_custom_init() -> None:
    """Test stub provider with custom parameters."""
    provider = StubMarketDataProvider(base_price=60000.0, spread_bps=5.0, volume=200.0)
    assert provider.base_price == 60000.0
    assert provider.spread_bps == 5.0
    assert provider.volume == 200.0


def test_get_candles_returns_correct_count() -> None:
    """Test get_candles returns requested number of candles."""
    provider = StubMarketDataProvider()
    candles = provider.get_candles("BTC/USDT", "5m", 10)
    assert len(candles) == 10


def test_get_candles_data_structure() -> None:
    """Test get_candles returns valid candle structure."""
    provider = StubMarketDataProvider(base_price=50000.0)
    candles = provider.get_candles("BTC/USDT", "5m", 5)

    for candle in candles:
        assert isinstance(candle.timestamp, datetime)
        assert candle.timestamp.tzinfo == timezone.utc
        assert candle.open == 50000.0
        assert candle.high == 50000.0 * 1.001
        assert candle.low == 50000.0 * 0.999
        assert candle.close == 50000.0 * 1.0005
        assert candle.volume == 100.0


def test_get_candles_timestamps_are_chronological() -> None:
    """Test get_candles returns chronologically ordered timestamps."""
    provider = StubMarketDataProvider()
    candles = provider.get_candles("BTC/USDT", "5m", 5)

    for i in range(len(candles) - 1):
        assert candles[i].timestamp < candles[i + 1].timestamp


def test_get_orderbook_returns_valid_structure() -> None:
    """Test get_orderbook returns valid orderbook."""
    provider = StubMarketDataProvider(base_price=50000.0, spread_bps=2.0)
    orderbook = provider.get_orderbook("BTC/USDT", 5)

    assert len(orderbook.bids) == 5
    assert len(orderbook.asks) == 5


def test_get_orderbook_spread_calculation() -> None:
    """Test get_orderbook calculates spread correctly."""
    provider = StubMarketDataProvider(base_price=50000.0, spread_bps=2.0)
    orderbook = provider.get_orderbook("BTC/USDT", 3)

    # 2 bps = 0.02% of 50000 = 10
    expected_spread = 50000.0 * (2.0 / 10000.0)
    expected_best_bid = 50000.0 - (expected_spread / 2)
    expected_best_ask = 50000.0 + (expected_spread / 2)

    assert orderbook.best_bid == expected_best_bid
    assert orderbook.best_ask == expected_best_ask


def test_get_orderbook_bids_descending() -> None:
    """Test get_orderbook bids are in descending order."""
    provider = StubMarketDataProvider()
    orderbook = provider.get_orderbook("BTC/USDT", 5)

    bid_prices = [price for price, _ in orderbook.bids]
    assert bid_prices == sorted(bid_prices, reverse=True)


def test_get_orderbook_asks_ascending() -> None:
    """Test get_orderbook asks are in ascending order."""
    provider = StubMarketDataProvider()
    orderbook = provider.get_orderbook("BTC/USDT", 5)

    ask_prices = [price for price, _ in orderbook.asks]
    assert ask_prices == sorted(ask_prices)


def test_get_orderbook_quantity_distribution() -> None:
    """Test get_orderbook has larger quantities at better prices."""
    provider = StubMarketDataProvider()
    orderbook = provider.get_orderbook("BTC/USDT", 3)

    # Best bid should have more quantity than worse bids
    assert orderbook.bids[0][1] > orderbook.bids[1][1]
    assert orderbook.bids[1][1] > orderbook.bids[2][1]

    # Best ask should have more quantity than worse asks
    assert orderbook.asks[0][1] > orderbook.asks[1][1]
    assert orderbook.asks[1][1] > orderbook.asks[2][1]


def test_get_orderbook_single_level() -> None:
    """Test get_orderbook with single depth level."""
    provider = StubMarketDataProvider()
    orderbook = provider.get_orderbook("BTC/USDT", 1)

    assert len(orderbook.bids) == 1
    assert len(orderbook.asks) == 1
