"""Trend Following Strategy."""

from quantsail_engine.config.models import BotConfig
from quantsail_engine.indicators.adx import calculate_adx
from quantsail_engine.indicators.ema import calculate_ema
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.strategy import StrategyOutput


class TrendStrategy:
    """Trend following strategy using EMA crossover and ADX."""

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> StrategyOutput:
        """
        Analyze market for trend signals.

        Rule: EMA fast > EMA slow AND ADX > threshold -> ENTER_LONG
        """
        # Ensure enough data
        # We need roughly 2*slow_period for ADX stability or just slow_period for EMA
        # ADX needs 2*period smoothing.
        trend_config = config.strategies.trend
        # 30 roughly for ADX default 14
        required_len = max(trend_config.ema_slow, trend_config.ema_fast, 30)

        if len(candles) < required_len:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="trend",
                rationale={"reason": "insufficient_data"},
            )

        closes = [c.close for c in candles]
        
        # Calculate indicators
        ema_fast = calculate_ema(closes, trend_config.ema_fast)
        ema_slow = calculate_ema(closes, trend_config.ema_slow)
        adx = calculate_adx(candles, 14) # Default ADX period

        # Get latest values
        current_ema_fast = ema_fast[-1]
        current_ema_slow = ema_slow[-1]
        current_adx = adx[-1]

        signal = SignalType.HOLD
        confidence = 0.0

        if current_ema_fast > current_ema_slow and current_adx > trend_config.adx_threshold:
            signal = SignalType.ENTER_LONG
            # Confidence based on ADX strength (e.g., 25-50 maps to 0.5-1.0)
            # Simple linear mapping: min(1.0, current_adx / 50.0)
            confidence = min(1.0, current_adx / 50.0)

        return StrategyOutput(
            signal=signal,
            confidence=confidence,
            strategy_name="trend",
            rationale={
                "ema_fast": current_ema_fast,
                "ema_slow": current_ema_slow,
                "adx": current_adx,
                "threshold": trend_config.adx_threshold,
            },
        )
