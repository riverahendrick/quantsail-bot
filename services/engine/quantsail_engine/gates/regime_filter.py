
import logging
import pandas as pd
import pandas_ta as ta
from quantsail_engine.config.models import RegimeConfig
from quantsail_engine.models.candle import Candle

logger = logging.getLogger(__name__)

class RegimeFilter:
    """
    Market Regime Filter to detect choppy/sideways markets.
    Uses ADX (Average Directional Index) and ATR (Average True Range).
    """

    def __init__(self, config: RegimeConfig):
        self.config = config

    def analyze(self, candles: list[Candle], symbol: str | None = None) -> bool:
        """Analyze market conditions and return True if trading is allowed.

        Args:
            candles: List of recent candles (must cover adx_period + lookback).
            symbol: Optional symbol for per-symbol threshold overrides.

        Returns:
            True if market conditions are favorable (e.g., trending), False if choppy.
        """
        if not self.config.enabled:
            return True

        if len(candles) < self.config.adx_period + 20:
            return True

        # Resolve per-symbol overrides
        adx_threshold = self.config.adx_threshold
        atr_threshold_pct = self.config.atr_threshold_pct

        if symbol and self.config.per_symbol_overrides:
            # Match by symbol prefix (e.g. "BTC/USDT" matches "BTC" key)
            for key, override in self.config.per_symbol_overrides.items():
                if symbol.startswith(key) or symbol == key:
                    if override.adx_threshold is not None:
                        adx_threshold = override.adx_threshold
                    if override.atr_threshold_pct is not None:
                        atr_threshold_pct = override.atr_threshold_pct
                    break

        # Convert to DataFrame
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
        adx_df = ta.adx(high=df['high'], low=df['low'], close=df['close'], length=self.config.adx_period)

        if adx_df is None or adx_df.empty:
            logger.warning("Could not calculate ADX for regime filter.")
            return True

        current_adx = adx_df[f"ADX_{self.config.adx_period}"].iloc[-1]

        # Calculate ATR%
        atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=self.config.atr_period)
        if atr is None or atr.empty:
            logger.warning("Could not calculate ATR for regime filter.")
            return True

        current_atr = atr.iloc[-1]
        current_close = df['close'].iloc[-1]
        current_atr_pct = (current_atr / current_close) * 100

        is_trending = current_adx >= adx_threshold
        is_volatile = current_atr_pct >= atr_threshold_pct

        can_trade = is_trending and is_volatile

        if not can_trade:
            logger.debug(
                f"Regime Filter blocking trade. ADX={current_adx:.2f} "
                f"(Thresh={adx_threshold}), ATR%={current_atr_pct:.2f} "
                f"(Thresh={atr_threshold_pct})"
                + (f" [symbol={symbol}]" if symbol else "")
            )

        return can_trade
