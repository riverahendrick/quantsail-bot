"""Ensemble strategy combiner."""

import logging

from quantsail_engine.config.models import BotConfig
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import Signal, SignalType
from quantsail_engine.models.strategy import StrategyOutput
from quantsail_engine.strategies.breakout import BreakoutStrategy
from quantsail_engine.strategies.interface import Strategy
from quantsail_engine.strategies.mean_reversion import MeanReversionStrategy
from quantsail_engine.strategies.trend import TrendStrategy

logger = logging.getLogger(__name__)


class EnsembleCombiner:
    """Combines outputs from multiple strategies to form a consensus."""

    def __init__(self) -> None:
        """Initialize strategies."""
        self.strategies: list[Strategy] = [
            TrendStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
        ]

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> Signal:
        """
        Run all strategies and combine results.

        Args:
            symbol: Trading symbol.
            candles: List of candles.
            orderbook: Orderbook snapshot.
            config: Bot configuration.

        Returns:
            Signal with strategy outputs included.
        """
        outputs: list[StrategyOutput] = []
        votes = 0
        conf_sum = 0.0

        for strategy in self.strategies:
            try:
                output = strategy.analyze(symbol, candles, orderbook, config)
                outputs.append(output)
                
                if (
                    output.signal == SignalType.ENTER_LONG
                    and output.confidence >= config.strategies.ensemble.confidence_threshold
                ):
                    votes += 1
                    conf_sum += output.confidence
            except Exception as e:
                logger.error(f"Strategy {strategy} failed: {e}", exc_info=True)
                # Fail safe: add a neutral/HOLD output
                outputs.append(
                    StrategyOutput(
                        signal=SignalType.HOLD,
                        confidence=0.0,
                        strategy_name=type(strategy).__name__,
                        rationale={"error": str(e)},
                    )
                )

        # Consensus Logic
        min_agreement = config.strategies.ensemble.min_agreement
        
        final_signal = SignalType.HOLD
        avg_confidence = 0.0

        if votes >= min_agreement:
            final_signal = SignalType.ENTER_LONG
            avg_confidence = conf_sum / votes if votes > 0 else 0.0

        return Signal(
            signal_type=final_signal,
            symbol=symbol,
            confidence=avg_confidence,
            strategy_outputs=outputs,
        )
