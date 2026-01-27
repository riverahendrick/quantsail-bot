"""Unit tests for StubSignalProvider."""

from datetime import datetime, timezone

from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.signals.stub_provider import StubSignalProvider


def test_stub_signal_provider_default_hold() -> None:
    """Test stub provider defaults to HOLD signal."""
    provider = StubSignalProvider()
    candles = [
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    orderbook = Orderbook(bids=[(50000.0, 10.0)], asks=[(50001.0, 10.0)])

    signal = provider.generate_signal("BTC/USDT", candles, orderbook)

    assert signal.signal_type == SignalType.HOLD
    assert signal.symbol == "BTC/USDT"
    assert signal.confidence == 1.0


def test_stub_signal_provider_set_enter_long() -> None:
    """Test stub provider returns ENTER_LONG after set_next_signal."""
    provider = StubSignalProvider()
    provider.set_next_signal(SignalType.ENTER_LONG)

    candles = [
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    orderbook = Orderbook(bids=[(50000.0, 10.0)], asks=[(50001.0, 10.0)])

    signal = provider.generate_signal("ETH/USDT", candles, orderbook)

    assert signal.signal_type == SignalType.ENTER_LONG
    assert signal.symbol == "ETH/USDT"
    assert signal.confidence == 1.0


def test_stub_signal_provider_set_exit() -> None:
    """Test stub provider returns EXIT after set_next_signal."""
    provider = StubSignalProvider()
    provider.set_next_signal(SignalType.EXIT)

    candles = [
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    orderbook = Orderbook(bids=[(50000.0, 10.0)], asks=[(50001.0, 10.0)])

    signal = provider.generate_signal("BTC/USDT", candles, orderbook)

    assert signal.signal_type == SignalType.EXIT
    assert signal.symbol == "BTC/USDT"


def test_stub_signal_provider_multiple_calls() -> None:
    """Test stub provider returns same signal across multiple calls."""
    provider = StubSignalProvider()
    provider.set_next_signal(SignalType.ENTER_LONG)

    candles = [
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    orderbook = Orderbook(bids=[(50000.0, 10.0)], asks=[(50001.0, 10.0)])

    signal1 = provider.generate_signal("BTC/USDT", candles, orderbook)
    signal2 = provider.generate_signal("BTC/USDT", candles, orderbook)

    assert signal1.signal_type == SignalType.ENTER_LONG
    assert signal2.signal_type == SignalType.ENTER_LONG


def test_stub_signal_provider_change_signal() -> None:
    """Test stub provider can change signal between calls."""
    provider = StubSignalProvider()

    candles = [
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    orderbook = Orderbook(bids=[(50000.0, 10.0)], asks=[(50001.0, 10.0)])

    # First: ENTER_LONG
    provider.set_next_signal(SignalType.ENTER_LONG)
    signal1 = provider.generate_signal("BTC/USDT", candles, orderbook)
    assert signal1.signal_type == SignalType.ENTER_LONG

    # Then: EXIT
    provider.set_next_signal(SignalType.EXIT)
    signal2 = provider.generate_signal("BTC/USDT", candles, orderbook)
    assert signal2.signal_type == SignalType.EXIT

    # Then: HOLD
    provider.set_next_signal(SignalType.HOLD)
    signal3 = provider.generate_signal("BTC/USDT", candles, orderbook)
    assert signal3.signal_type == SignalType.HOLD
