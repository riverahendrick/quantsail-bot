"""Ensemble signal provider implementation."""

from quantsail_engine.config.models import BotConfig
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import Signal
from quantsail_engine.signals.provider import SignalProvider
from quantsail_engine.strategies.ensemble import EnsembleCombiner


class EnsembleSignalProvider(SignalProvider):
    """Signal provider using ensemble strategy logic."""

    def __init__(self, config: BotConfig) -> None:
        """
        Initialize ensemble provider.

        Args:
            config: Bot configuration.
        """
        self.config = config
        self.combiner = EnsembleCombiner()

    def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
    ) -> Signal:
        """
        Generate signal using ensemble combiner.

        Args:
            symbol: Trading symbol.
            candles: List of candles.
            orderbook: Orderbook snapshot.

        Returns:
            Signal with embedded strategy outputs.
        """
        return self.combiner.analyze(symbol, candles, orderbook, self.config)
