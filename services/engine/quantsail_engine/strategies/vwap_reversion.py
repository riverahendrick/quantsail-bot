"""VWAP Mean Reversion Strategy."""

from quantsail_engine.config.models import BotConfig
from quantsail_engine.indicators.obv import calculate_obv
from quantsail_engine.indicators.rsi import calculate_rsi
from quantsail_engine.indicators.vwap import calculate_vwap
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.strategy import StrategyOutput


class VWAPReversionStrategy:
    """
    VWAP Mean Reversion strategy.

    Entry signal: Price is significantly below VWAP + RSI oversold + OBV uptick.
    This targets mean-reversion opportunities in ranging markets.
    """

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        orderbook: Orderbook,
        config: BotConfig,
    ) -> StrategyOutput:
        """
        Analyze market for VWAP mean reversion signals.

        Rule: Price < VWAP * (1 - deviation%) AND RSI < oversold AND OBV rising
        """
        vwap_config = config.strategies.vwap_reversion

        if not vwap_config.enabled:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="vwap_reversion",
                rationale={"reason": "disabled"},
            )

        required_len = max(vwap_config.rsi_period + 1, 5)
        if len(candles) < required_len:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="vwap_reversion",
                rationale={"reason": "insufficient_data"},
            )

        # Calculate indicators
        vwap = calculate_vwap(candles)
        current_vwap = vwap[-1]

        if current_vwap <= 0:
            return StrategyOutput(
                signal=SignalType.HOLD,
                confidence=0.0,
                strategy_name="vwap_reversion",
                rationale={"reason": "invalid_vwap"},
            )

        closes = [c.close for c in candles]
        current_price = closes[-1]

        rsi_values = calculate_rsi(closes, vwap_config.rsi_period)
        current_rsi = rsi_values[-1]

        # Check OBV trend (confirmation)
        obv = calculate_obv(candles)
        # Smoothed OBV trend: 3-candle average comparison (less noisy on 5m)
        if len(obv) >= 6:
            obv_rising = sum(obv[-3:]) / 3.0 > sum(obv[-6:-3]) / 3.0
        elif len(obv) >= 2:
            obv_rising = obv[-1] > obv[-2]
        else:
            obv_rising = False

        # Calculate deviation from VWAP
        deviation_pct = ((current_vwap - current_price) / current_vwap) * 100.0

        signal = SignalType.HOLD
        confidence = 0.0

        # Entry conditions
        price_below_vwap = deviation_pct >= vwap_config.deviation_entry_pct
        rsi_oversold = current_rsi > 0 and current_rsi < vwap_config.rsi_oversold
        obv_ok = (not vwap_config.obv_confirmation) or obv_rising

        if price_below_vwap and rsi_oversold and obv_ok:
            signal = SignalType.ENTER_LONG

            # Confidence: blend of deviation and RSI severity
            dev_score = min(deviation_pct / (vwap_config.deviation_entry_pct * 2), 1.0)
            rsi_score = (
                (vwap_config.rsi_oversold - current_rsi) / max(vwap_config.rsi_oversold, 1.0)
                if vwap_config.rsi_oversold > 0
                else 0.5
            )
            # Floor at 0.5: conditions are already met, so base confidence is meaningful
            confidence = max(0.5, (dev_score + rsi_score) / 2.0)

        return StrategyOutput(
            signal=signal,
            confidence=confidence,
            strategy_name="vwap_reversion",
            rationale={
                "price": current_price,
                "vwap": current_vwap,
                "deviation_pct": deviation_pct,
                "rsi": current_rsi,
                "obv_rising": obv_rising,
                "entry_threshold_pct": vwap_config.deviation_entry_pct,
            },
        )
