"""Stub signal provider for testing with controllable signals."""

from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import Signal, SignalType

from .provider import SignalProvider


class StubSignalProvider(SignalProvider):
    """Stub provider returning controllable signals for testing."""

    def __init__(self) -> None:
        """Initialize stub provider with default HOLD signal."""
        self._next_signal: SignalType = SignalType.HOLD

    def set_next_signal(self, signal_type: SignalType) -> None:
        """
        Set the next signal to return.

        Args:
            signal_type: Signal type to return on next generate_signal() call
        """
        self._next_signal = signal_type

    def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
    ) -> Signal:
        """Return the pre-configured signal."""
        return Signal(signal_type=self._next_signal, symbol=symbol, confidence=1.0)
