"""Unit tests for Candle and Orderbook models."""

from datetime import datetime, timezone

import pytest

from quantsail_engine.models.candle import Candle, Orderbook


def test_candle_creation_valid() -> None:
    """Test creating a valid candle."""
    candle = Candle(
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=100.5,
    )
    assert candle.open == 50000.0
    assert candle.high == 51000.0
    assert candle.low == 49000.0
    assert candle.close == 50500.0
    assert candle.volume == 100.5


def test_candle_high_below_open() -> None:
    """Test candle validation rejects high < open."""
    with pytest.raises(ValueError, match="High must be >= open"):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=49000.0,  # Invalid
            low=48000.0,
            close=49500.0,
            volume=100.0,
        )


def test_candle_high_below_close() -> None:
    """Test candle validation rejects high < close."""
    with pytest.raises(ValueError, match="High must be >= open"):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=49000.0,
            high=49500.0,
            low=48000.0,
            close=50000.0,  # Close > high, invalid
            volume=100.0,
        )


def test_candle_low_above_open() -> None:
    """Test candle validation rejects low > open."""
    with pytest.raises(ValueError, match="Low must be <= open"):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=49000.0,
            high=51000.0,
            low=50000.0,  # Low > open, invalid
            close=49500.0,
            volume=100.0,
        )


def test_candle_low_above_close() -> None:
    """Test candle validation rejects low > close."""
    with pytest.raises(ValueError, match="Low must be <= open"):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=50500.0,  # Low > close, invalid
            close=50200.0,
            volume=100.0,
        )


def test_candle_negative_volume() -> None:
    """Test candle validation rejects negative volume."""
    with pytest.raises(ValueError, match="Volume must be non-negative"):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=-10.0,  # Invalid
        )


def test_candle_zero_volume() -> None:
    """Test candle allows zero volume."""
    candle = Candle(
        timestamp=datetime.now(timezone.utc),
        open=50000.0,
        high=50000.0,
        low=50000.0,
        close=50000.0,
        volume=0.0,
    )
    assert candle.volume == 0.0


def test_orderbook_creation_valid() -> None:
    """Test creating a valid orderbook."""
    orderbook = Orderbook(
        bids=[(50000.0, 1.0), (49999.0, 2.0), (49998.0, 3.0)],
        asks=[(50001.0, 1.0), (50002.0, 2.0), (50003.0, 3.0)],
    )
    assert orderbook.best_bid == 50000.0
    assert orderbook.best_ask == 50001.0
    assert orderbook.spread == 1.0
    assert orderbook.mid_price == 50000.5


def test_orderbook_empty_bids() -> None:
    """Test orderbook validation rejects empty bids."""
    with pytest.raises(ValueError, match="at least one bid"):
        Orderbook(
            bids=[],
            asks=[(50001.0, 1.0)],
        )


def test_orderbook_empty_asks() -> None:
    """Test orderbook validation rejects empty asks."""
    with pytest.raises(ValueError, match="at least one ask"):
        Orderbook(
            bids=[(50000.0, 1.0)],
            asks=[],
        )


def test_orderbook_bids_not_descending() -> None:
    """Test orderbook validation rejects bids not in descending order."""
    with pytest.raises(ValueError, match="descending order"):
        Orderbook(
            bids=[(49999.0, 1.0), (50000.0, 2.0)],  # Ascending, invalid
            asks=[(50001.0, 1.0)],
        )


def test_orderbook_asks_not_ascending() -> None:
    """Test orderbook validation rejects asks not in ascending order."""
    with pytest.raises(ValueError, match="ascending order"):
        Orderbook(
            bids=[(50000.0, 1.0)],
            asks=[(50002.0, 1.0), (50001.0, 2.0)],  # Descending, invalid
        )


def test_orderbook_properties() -> None:
    """Test orderbook computed properties."""
    orderbook = Orderbook(
        bids=[(100.0, 5.0), (99.5, 10.0)],
        asks=[(100.5, 3.0), (101.0, 7.0)],
    )
    assert orderbook.best_bid == 100.0
    assert orderbook.best_ask == 100.5
    assert orderbook.spread == 0.5
    assert orderbook.mid_price == 100.25
