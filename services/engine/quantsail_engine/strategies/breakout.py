"""Breakout Strategy."""

from quantsail_engine.config.models import BotConfig
from quantsail_engine.indicators.atr import calculate_atr
from quantsail_engine.indicators.donchian import calculate_donchian_channels
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.strategy import StrategyOutput


class BreakoutStrategy:
    """Breakout strategy using Donchian Channels and ATR."""

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> StrategyOutput:
        """
        Analyze market for breakout signals.

        Rule: Close > Donchian High (prev) + (ATR * mult) -> ENTER_LONG
        """
        bo_config = config.strategies.breakout
        required_len = max(bo_config.donchian_period, bo_config.atr_period) + 2
        
        if len(candles) < required_len:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="breakout",
                rationale={"reason": "insufficient_data"},
            )

        closes = [c.close for c in candles]
        current_price = closes[-1]

        # Calculate indicators
        donchian = calculate_donchian_channels(candles, bo_config.donchian_period)
        atr = calculate_atr(candles, bo_config.atr_period)

        # Previous Donchian High (from closed candle before current)
        # We index -2 because -1 is the current candle (forming)
        prev_high = donchian.high[-2]
        current_atr = atr[-1]

        signal = SignalType.HOLD
        confidence = 0.0
        
        breakout_level = prev_high + (current_atr * bo_config.atr_filter_mult)

        if current_price > breakout_level:
            signal = SignalType.ENTER_LONG
            # Confidence increases as price moves further away
            # e.g. (Price - Level) / ATR
            if current_atr > 0:
                excess = (current_price - breakout_level) / current_atr
                confidence = min(1.0, 0.5 + (excess * 0.5)) # Base 0.5, adds up to 1.0
            else:
                confidence = 0.5

        return StrategyOutput(
            signal=signal,
            confidence=confidence,
            strategy_name="breakout",
            rationale={
                "price": current_price,
                "prev_donchian_high": prev_high,
                "atr": current_atr,
                "breakout_level": breakout_level,
            },
        )
