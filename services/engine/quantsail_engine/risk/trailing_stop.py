"""Trailing stop-loss manager."""

from quantsail_engine.config.models import TrailingStopConfig


class TrailingStopManager:
    """
    Manages trailing stop-loss levels for open positions.

    Supports three methods:
    - pct: Fixed percentage trail below highest price
    - atr: ATR-multiple trail below highest price
    - chandelier: ATR from the highest high (Chandelier Exit)

    The trailing stop only ratchets up — never down.
    """

    def __init__(self, config: TrailingStopConfig) -> None:
        self.config = config
        # Per-position state: trade_id -> (highest_price, current_stop)
        self._state: dict[str, tuple[float, float]] = {}
        # Track entry prices for activation threshold
        self._entry_prices: dict[str, float] = {}

    def init_position(
        self,
        trade_id: str,
        entry_price: float,
        initial_stop: float,
    ) -> float:
        """
        Initialize trailing stop for a new position.

        Args:
            trade_id: Unique trade identifier.
            entry_price: Trade entry price.
            initial_stop: Initial stop-loss price.

        Returns:
            Current stop-loss level.
        """
        self._state[trade_id] = (entry_price, initial_stop)
        self._entry_prices[trade_id] = entry_price
        return initial_stop

    def update(
        self,
        trade_id: str,
        current_price: float,
        atr_value: float = 0.0,
    ) -> float:
        """
        Update the trailing stop based on current market data.

        Args:
            trade_id: Unique trade identifier.
            current_price: Current market price.
            atr_value: Current ATR value (for atr/chandelier methods).

        Returns:
            Updated stop-loss level.
        """
        if not self.config.enabled or trade_id not in self._state:
            return self._state.get(trade_id, (0, 0))[1]

        highest_price, current_stop = self._state[trade_id]

        # Update highest price
        if current_price > highest_price:
            highest_price = current_price

        # Check activation threshold
        entry_price = self._entry_prices.get(trade_id, 0.0)
        if entry_price > 0:
            profit_pct = ((highest_price - entry_price) / entry_price) * 100.0
            if profit_pct < self.config.activation_pct:
                # Not yet activated — keep current stop
                self._state[trade_id] = (highest_price, current_stop)
                return current_stop

        # Calculate new trailing stop
        if self.config.method == "pct":
            new_stop = highest_price * (1.0 - self.config.trail_pct / 100.0)

        elif self.config.method in ("atr", "chandelier"):
            if atr_value > 0:
                new_stop = highest_price - (atr_value * self.config.atr_multiplier)
            else:
                new_stop = current_stop

        else:
            new_stop = current_stop

        # Trailing stop only ratchets up, never down
        final_stop = max(new_stop, current_stop)
        self._state[trade_id] = (highest_price, final_stop)
        return final_stop

    def should_exit(
        self,
        trade_id: str,
        current_price: float,
        atr_value: float = 0.0,
    ) -> bool:
        """
        Check if current price has hit the trailing stop.

        Args:
            trade_id: Unique trade identifier.
            current_price: Current market price.
            atr_value: Current ATR value.

        Returns:
            True if current_price <= trailing stop level.
        """
        if not self.config.enabled:
            return False

        stop_level = self.update(trade_id, current_price, atr_value)
        return current_price <= stop_level

    def remove_position(self, trade_id: str) -> None:
        """Remove tracking state for a closed position."""
        self._state.pop(trade_id, None)
        self._entry_prices.pop(trade_id, None)

    def get_stop_level(self, trade_id: str) -> float | None:
        """Get current stop level for a position."""
        if trade_id in self._state:
            return self._state[trade_id][1]
        return None
