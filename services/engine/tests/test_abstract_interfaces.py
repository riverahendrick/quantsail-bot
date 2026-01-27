"""Tests for abstract interface compliance."""

import pytest

from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.candle import Candle
from quantsail_engine.signals.provider import SignalProvider


def test_market_data_provider_is_abstract() -> None:
    """Test that MarketDataProvider cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MarketDataProvider()  # type: ignore[abstract]


def test_signal_provider_is_abstract() -> None:
    """Test that SignalProvider cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SignalProvider()  # type: ignore[abstract]


def test_market_data_provider_abstract_methods() -> None:
    """Test that concrete implementations must implement abstract methods."""

    class IncompleteProvider(MarketDataProvider):
        def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
            return []  # pragma: no cover
        # Missing get_orderbook

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteProvider()  # type: ignore[abstract]


def test_signal_provider_abstract_methods() -> None:
    """Test that concrete implementations must implement abstract methods."""

    class IncompleteSignalProvider(SignalProvider):
        # Missing generate_signal
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteSignalProvider()  # type: ignore[abstract]
