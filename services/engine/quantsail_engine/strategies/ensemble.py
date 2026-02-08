"""Ensemble strategy combiner."""

import logging
from typing import ClassVar

from quantsail_engine.config.models import BotConfig
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import Signal, SignalType
from quantsail_engine.models.strategy import StrategyOutput
from quantsail_engine.strategies.breakout import BreakoutStrategy
from quantsail_engine.strategies.interface import Strategy
from quantsail_engine.strategies.mean_reversion import MeanReversionStrategy
from quantsail_engine.strategies.trend import TrendStrategy
from quantsail_engine.strategies.vwap_reversion import VWAPReversionStrategy

logger = logging.getLogger(__name__)


class EnsembleCombiner:
    """Combines outputs from multiple strategies to form a consensus.

    Supports two modes:
    - agreement: Original mode — requires min N strategies to agree
    - weighted: Each strategy gets a configurable weight; total score must exceed threshold
    """

    # Maps strategy names to their config weight attribute names
    WEIGHT_MAP: ClassVar[dict[str, str]] = {
        "trend": "weight_trend",
        "mean_reversion": "weight_mean_reversion",
        "breakout": "weight_breakout",
        "vwap_reversion": "weight_vwap",
    }

    def __init__(self) -> None:
        """Initialize strategies."""
        self.strategies: list[Strategy] = [
            TrendStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            VWAPReversionStrategy(),
        ]

    def _resolve_ensemble_params(
        self, symbol: str, config: BotConfig,
    ) -> tuple[dict[str, float], int, float, float]:
        """Resolve effective ensemble params for a symbol.

        Checks per_coin_overrides first, falling back to global values.

        Returns:
            Tuple of (weight_map, min_agreement, confidence_threshold, weighted_threshold)
        """
        ensemble = config.strategies.ensemble

        # Normalize symbol: strip /USDT suffix for lookup
        clean_sym = symbol.replace("/USDT", "").replace("_USDT", "")
        override = ensemble.per_coin_overrides.get(
            clean_sym, ensemble.per_coin_overrides.get(symbol)
        )

        # Weights: override fields if set, else global
        weights = {
            "weight_trend": (
                override.weight_trend if override and override.weight_trend is not None
                else ensemble.weight_trend
            ),
            "weight_mean_reversion": (
                override.weight_mean_reversion if override and override.weight_mean_reversion is not None
                else ensemble.weight_mean_reversion
            ),
            "weight_breakout": (
                override.weight_breakout if override and override.weight_breakout is not None
                else ensemble.weight_breakout
            ),
            "weight_vwap": (
                override.weight_vwap if override and override.weight_vwap is not None
                else ensemble.weight_vwap
            ),
        }

        min_agree = (
            override.min_agreement if override and override.min_agreement is not None
            else ensemble.min_agreement
        )
        conf_thresh = (
            override.confidence_threshold if override and override.confidence_threshold is not None
            else ensemble.confidence_threshold
        )
        wt_thresh = (
            override.weighted_threshold if override and override.weighted_threshold is not None
            else ensemble.weighted_threshold
        )

        return weights, min_agree, conf_thresh, wt_thresh

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

        for strategy in self.strategies:
            try:
                output = strategy.analyze(symbol, candles, orderbook, config)
                outputs.append(output)
            except Exception as e:
                logger.error(f"Strategy {strategy} failed: {e}", exc_info=True)
                outputs.append(
                    StrategyOutput(
                        signal=SignalType.HOLD,
                        confidence=0.0,
                        strategy_name=type(strategy).__name__,
                        rationale={"error": str(e)},
                    )
                )

        ensemble_config = config.strategies.ensemble

        if ensemble_config.mode == "weighted":
            return self._weighted_consensus(symbol, outputs, config)
        else:
            return self._agreement_consensus(symbol, outputs, config)

    def _agreement_consensus(
        self,
        symbol: str,
        outputs: list[StrategyOutput],
        config: BotConfig,
    ) -> Signal:
        """Original agreement mode: min N strategies must vote ENTER_LONG."""
        _, min_agree, conf_thresh, _ = self._resolve_ensemble_params(symbol, config)
        votes = 0
        conf_sum = 0.0

        for output in outputs:
            if (
                output.signal == SignalType.ENTER_LONG
                and output.confidence >= conf_thresh
            ):
                votes += 1
                conf_sum += output.confidence

        final_signal = SignalType.HOLD
        avg_confidence = 0.0

        if votes >= min_agree:
            final_signal = SignalType.ENTER_LONG
            avg_confidence = conf_sum / votes if votes > 0 else 0.0

        return Signal(
            signal_type=final_signal,
            symbol=symbol,
            confidence=avg_confidence,
            strategy_outputs=outputs,
        )

    def _weighted_consensus(
        self,
        symbol: str,
        outputs: list[StrategyOutput],
        config: BotConfig,
    ) -> Signal:
        """Weighted scoring mode: each strategy contributes weight * confidence.

        Uses per-coin weight overrides when available, falling back to global.
        """
        weights, _, _, wt_thresh = self._resolve_ensemble_params(symbol, config)
        total_score = 0.0
        total_weight = 0.0

        for output in outputs:
            weight_attr = self.WEIGHT_MAP.get(output.strategy_name, None)
            if weight_attr:
                weight = weights.get(weight_attr, 0.0)
            else:
                weight = 0.0

            if output.signal == SignalType.ENTER_LONG and output.confidence > 0:
                total_score += weight * output.confidence
            total_weight += weight

        # Normalize score to 0-1 range
        normalized_score = total_score / total_weight if total_weight > 0 else 0.0

        final_signal = SignalType.HOLD
        if normalized_score >= wt_thresh:
            final_signal = SignalType.ENTER_LONG

        return Signal(
            signal_type=final_signal,
            symbol=symbol,
            confidence=normalized_score,
            strategy_outputs=outputs,
        )
