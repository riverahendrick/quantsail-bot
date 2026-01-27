"""Strategy interface definition."""

from typing import Protocol

from quantsail_engine.config.models import BotConfig
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.strategy import StrategyOutput


class Strategy(Protocol):
    """Interface for trading strategies."""

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> StrategyOutput:
        """
        Analyze market data and return a trading signal.

        Args:
            symbol: Trading symbol.
            candles: List of candles (newest last).
            orderbook: Current orderbook snapshot.
            config: Bot configuration.

        Returns:
            StrategyOutput with signal, confidence, and rationale.
        """
        ...
