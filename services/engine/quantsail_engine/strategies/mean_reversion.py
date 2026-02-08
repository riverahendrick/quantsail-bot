"""Mean Reversion Strategy."""

from quantsail_engine.config.models import BotConfig
from quantsail_engine.indicators.bollinger import calculate_bollinger_bands
from quantsail_engine.indicators.rsi import calculate_rsi
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.strategy import StrategyOutput


class MeanReversionStrategy:
    """Mean reversion strategy using Bollinger Bands and RSI."""

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> StrategyOutput:
        """
        Analyze market for mean reversion signals.

        Rule: Price <= Lower BB AND RSI < oversold -> ENTER_LONG
        """
        mr_config = config.strategies.mean_reversion
        required_len = max(mr_config.bb_period, mr_config.rsi_period) + 1
        
        if len(candles) < required_len:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="mean_reversion",
                rationale={"reason": "insufficient_data"},
            )

        closes = [c.close for c in candles]
        current_price = closes[-1]

        # Calculate indicators
        bb = calculate_bollinger_bands(
            closes, mr_config.bb_period, mr_config.bb_std_dev
        )
        rsi = calculate_rsi(closes, mr_config.rsi_period)

        current_lower_bb = bb.lower[-1]
        current_rsi = rsi[-1]

        signal = SignalType.HOLD
        confidence = 0.0

        current_upper_bb = bb.upper[-1]

        if current_price <= current_lower_bb and current_rsi < mr_config.rsi_oversold:
            signal = SignalType.ENTER_LONG

            # Professional confidence: blend RSI depth + BB penetration depth
            # RSI component: how far below oversold (0-1 scale, capped)
            rsi_depth = min(
                (mr_config.rsi_oversold - current_rsi) / max(mr_config.rsi_oversold, 1.0),
                1.0,
            )

            # BB component: how far below lower band relative to band width
            band_width = current_upper_bb - current_lower_bb
            if band_width > 0 and current_price < current_lower_bb:
                bb_depth = min((current_lower_bb - current_price) / band_width, 1.0)
            else:
                bb_depth = 0.0

            # Weighted blend with floor of 0.5 (conditions already met = base confidence)
            confidence = max(0.5, rsi_depth * 0.6 + bb_depth * 0.4)

        return StrategyOutput(
            signal=signal,
            confidence=confidence,
            strategy_name="mean_reversion",
            rationale={
                "price": current_price,
                "lower_bb": current_lower_bb,
                "rsi": current_rsi,
                "rsi_oversold": mr_config.rsi_oversold,
            },
        )
