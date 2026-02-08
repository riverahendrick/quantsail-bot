"""Dynamic position sizer based on configurable methods."""

from quantsail_engine.config.models import PositionSizingConfig


class DynamicSizer:
    """
    Calculate position size dynamically based on the configured method.

    Supports three methods:
    - fixed: Static quantity from config
    - risk_pct: ATR-based risk sizing (risk_pct of equity / SL distance)
    - kelly: Kelly criterion fraction of equity
    """

    def __init__(self, config: PositionSizingConfig) -> None:
        self.config = config

    def calculate(
        self,
        equity_usd: float,
        entry_price: float,
        atr_value: float,
        sl_distance: float | None = None,
        win_rate: float | None = None,
        avg_win_loss_ratio: float | None = None,
    ) -> float:
        """
        Calculate position quantity.

        Args:
            equity_usd: Current portfolio equity in USD.
            entry_price: Expected entry price.
            atr_value: Current ATR value (used for risk_pct method).
            sl_distance: Stop-loss distance in price units (if None, uses 2*ATR).
            win_rate: Historical win rate 0-1 (for kelly method).
            avg_win_loss_ratio: Average win/loss ratio (for kelly method).

        Returns:
            Position quantity (in base currency units, e.g. BTC).
        """
        if entry_price <= 0:
            return 0.0

        if self.config.method == "fixed":
            quantity = self.config.fixed_quantity

        elif self.config.method == "risk_pct":
            quantity = self._risk_pct_size(equity_usd, entry_price, atr_value, sl_distance)

        elif self.config.method == "kelly":
            quantity = self._kelly_size(equity_usd, entry_price, win_rate, avg_win_loss_ratio)

        else:
            quantity = self.config.fixed_quantity

        # Apply max position cap
        max_position_usd = equity_usd * (self.config.max_position_pct / 100.0)
        max_quantity = max_position_usd / entry_price
        quantity = min(quantity, max_quantity)

        return max(quantity, 0.0)

    def _risk_pct_size(
        self,
        equity_usd: float,
        entry_price: float,
        atr_value: float,
        sl_distance: float | None,
    ) -> float:
        """
        Risk-percentage sizing: risk_pct of equity / SL distance.

        Position size = (equity * risk%) / (SL distance in $)
        """
        risk_usd = equity_usd * (self.config.risk_pct / 100.0)

        # SL distance in price units
        stop_distance = sl_distance if sl_distance and sl_distance > 0 else atr_value * 2.0

        if stop_distance <= 0:
            return self.config.fixed_quantity

        # Quantity = risk in USD / stop distance per unit
        return risk_usd / stop_distance

    def _kelly_size(
        self,
        equity_usd: float,
        entry_price: float,
        win_rate: float | None,
        avg_ratio: float | None,
    ) -> float:
        """
        Kelly criterion sizing: f* = (p * b - q) / b

        Where: p = win_rate, q = 1 - p, b = avg_win/avg_loss ratio
        Applied as fraction-Kelly (e.g., 0.25 = quarter-Kelly).
        """
        p = win_rate if win_rate and 0 < win_rate < 1 else 0.5
        b = avg_ratio if avg_ratio and avg_ratio > 0 else 1.5

        q = 1.0 - p
        kelly_f = (p * b - q) / b

        if kelly_f <= 0:
            # Kelly says don't bet — fall back to minimum position
            return self.config.fixed_quantity

        # Apply fractional Kelly
        position_usd = equity_usd * kelly_f * self.config.kelly_fraction
        return position_usd / entry_price
