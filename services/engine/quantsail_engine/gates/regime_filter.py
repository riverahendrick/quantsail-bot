"""Market Regime Filter — strategy-aware market condition analysis.

Instead of a simple bool gate (trending AND volatile), this filter now
returns a RegimeState enum so the caller can route different strategy
types to appropriate market conditions:

  TRENDING     → momentum/trend-following strategies
  RANGING      → mean-reversion / grid strategies
  VOLATILE     → volatility-breakout strategies
  QUIET        → no strategies (too little movement)
  UNKNOWN      → data insufficient, default to allow
"""

import enum
import logging
from typing import Any

import pandas as pd
import pandas_ta as ta

from quantsail_engine.config.models import RegimeConfig
from quantsail_engine.models.candle import Candle

logger = logging.getLogger(__name__)


class RegimeState(str, enum.Enum):
    """Detected market regime."""

    TRENDING = "TRENDING"       # ADX high, clear direction
    RANGING = "RANGING"         # ADX low, low ATR% → sideways
    VOLATILE = "VOLATILE"       # High ATR% but low ADX → choppy but moving
    QUIET = "QUIET"             # Low ADX and low ATR% → dead market
    UNKNOWN = "UNKNOWN"         # Insufficient data


# Which regimes allow which strategy families
_STRATEGY_REGIME_MAP: dict[str, set[RegimeState]] = {
    "momentum": {RegimeState.TRENDING, RegimeState.VOLATILE},
    "trend": {RegimeState.TRENDING},
    "mean_reversion": {RegimeState.RANGING, RegimeState.VOLATILE},
    "grid": {RegimeState.RANGING, RegimeState.VOLATILE, RegimeState.TRENDING},
    "breakout": {RegimeState.VOLATILE, RegimeState.TRENDING},
    "default": {RegimeState.TRENDING, RegimeState.VOLATILE},
}


class RegimeFilter:
    """Market Regime Filter to detect and classify market conditions.

    Uses ADX (Average Directional Index) and ATR (Average True Range).
    """

    def __init__(self, config: RegimeConfig) -> None:
        self.config = config

    def classify(
        self,
        candles: list[Candle],
        symbol: str | None = None,
    ) -> RegimeState:
        """Classify the current market regime.

        Args:
            candles: Recent price candles (need at least adx_period + 20).
            symbol: Optional symbol for per-symbol threshold overrides.

        Returns:
            A RegimeState enum indicating the detected market condition.
        """
        if not self.config.enabled:
            return RegimeState.TRENDING  # Filter disabled → assume favorable

        if len(candles) < self.config.adx_period + 20:
            return RegimeState.UNKNOWN

        # Resolve per-symbol overrides
        adx_threshold = self.config.adx_threshold
        atr_threshold_pct = self.config.atr_threshold_pct

        if symbol and self.config.per_symbol_overrides:
            for key, override in self.config.per_symbol_overrides.items():
                if symbol.startswith(key) or symbol == key:
                    if override.adx_threshold is not None:
                        adx_threshold = override.adx_threshold
                    if override.atr_threshold_pct is not None:
                        atr_threshold_pct = override.atr_threshold_pct
                    break

        # Build DataFrame
        data = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        df = pd.DataFrame(data)

        # Calculate ADX
        adx_df = ta.adx(
            high=df["high"], low=df["low"], close=df["close"],
            length=self.config.adx_period,
        )
        if adx_df is None or adx_df.empty:
            logger.warning("Could not calculate ADX for regime filter.")
            return RegimeState.UNKNOWN

        current_adx: float = adx_df[f"ADX_{self.config.adx_period}"].iloc[-1]

        # Calculate ATR%
        atr = ta.atr(
            high=df["high"], low=df["low"], close=df["close"],
            length=self.config.atr_period,
        )
        if atr is None or atr.empty:
            logger.warning("Could not calculate ATR for regime filter.")
            return RegimeState.UNKNOWN

        current_atr: float = atr.iloc[-1]
        current_close: float = df["close"].iloc[-1]
        current_atr_pct = (current_atr / current_close) * 100

        is_trending = current_adx >= adx_threshold
        is_volatile = current_atr_pct >= atr_threshold_pct

        if is_trending and is_volatile:
            regime = RegimeState.TRENDING
        elif is_trending and not is_volatile:
            regime = RegimeState.TRENDING  # Trending but calm — still tradeable
        elif not is_trending and is_volatile:
            regime = RegimeState.VOLATILE
        elif not is_trending and current_atr_pct < atr_threshold_pct * 0.5:
            regime = RegimeState.QUIET
        else:
            regime = RegimeState.RANGING

        logger.debug(
            "Regime: %s (ADX=%.2f thresh=%s, ATR%%=%.2f thresh=%s)%s",
            regime.value, current_adx, adx_threshold,
            current_atr_pct, atr_threshold_pct,
            f" [symbol={symbol}]" if symbol else "",
        )

        return regime

    def analyze(
        self,
        candles: list[Candle],
        symbol: str | None = None,
        strategy_type: str | None = None,
    ) -> bool:
        """Check whether the current regime allows trading.

        Backward-compatible wrapper around classify().

        Args:
            candles: Recent price candles.
            symbol: Optional symbol for per-symbol overrides.
            strategy_type: Strategy family (e.g. 'momentum', 'grid', 'mean_reversion').
                           If None, uses 'default' map.

        Returns:
            True if the current regime allows the given strategy type.
        """
        regime = self.classify(candles, symbol=symbol)

        if regime == RegimeState.UNKNOWN:
            return True  # Insufficient data → allow

        allowed = _STRATEGY_REGIME_MAP.get(
            strategy_type or "default",
            _STRATEGY_REGIME_MAP["default"],
        )

        can_trade = regime in allowed

        if not can_trade:
            logger.debug(
                "Regime filter blocking %s strategy in %s regime",
                strategy_type or "default", regime.value,
            )

        return can_trade
