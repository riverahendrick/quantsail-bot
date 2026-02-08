"""Daily per-symbol consecutive loss limit gate."""

import logging
from datetime import datetime

from quantsail_engine.config.models import DailySymbolLimitConfig

logger = logging.getLogger(__name__)


class DailySymbolLossLimit:
    """Pauses trading on a symbol after N consecutive losses in a UTC day.

    Resets on: (a) new UTC day, (b) a winning trade on the same symbol.
    """

    def __init__(self, config: DailySymbolLimitConfig) -> None:
        """Initialize DailySymbolLossLimit.

        Args:
            config: Daily symbol limit configuration.
        """
        self.config = config
        # symbol -> (consecutive_losses, last_loss_date_str)
        self._symbol_state: dict[str, tuple[int, str]] = {}

    def _get_date_str(self, timestamp: datetime) -> str:
        """Get UTC date string from timestamp."""
        return timestamp.strftime("%Y-%m-%d")

    def record_loss(self, symbol: str, timestamp: datetime) -> None:
        """Record a losing trade for a symbol.

        Args:
            symbol: Trading symbol.
            timestamp: Time of the loss.
        """
        if not self.config.enabled:
            return

        date_str = self._get_date_str(timestamp)
        current = self._symbol_state.get(symbol)

        if current is None or current[1] != date_str:
            # New day or first loss ever — start fresh
            self._symbol_state[symbol] = (1, date_str)
        else:
            # Same day — increment
            self._symbol_state[symbol] = (current[0] + 1, date_str)

        losses = self._symbol_state[symbol][0]
        logger.info(
            f"Daily loss #{losses} for {symbol} on {date_str}"
        )

    def record_win(self, symbol: str, timestamp: datetime) -> None:
        """Record a winning trade — resets consecutive loss counter.

        Args:
            symbol: Trading symbol.
            timestamp: Time of the win.
        """
        if not self.config.enabled:
            return

        date_str = self._get_date_str(timestamp)
        self._symbol_state[symbol] = (0, date_str)

    def is_allowed(
        self, symbol: str, current_time: datetime
    ) -> tuple[bool, str | None]:
        """Check if trading is allowed for the symbol today.

        Args:
            symbol: Trading symbol.
            current_time: Current simulation or wall-clock time.

        Returns:
            Tuple of (allowed, rejection_reason).
        """
        if not self.config.enabled:
            return True, None

        current = self._symbol_state.get(symbol)
        if current is None:
            return True, None

        losses, date_str = current
        today = self._get_date_str(current_time)

        # New day resets the counter
        if date_str != today:
            return True, None

        if losses >= self.config.max_consecutive_losses:
            reason = (
                f"daily_symbol_loss_limit "
                f"({losses} consecutive losses today, max={self.config.max_consecutive_losses})"
            )
            return False, reason

        return True, None

    def reset(self) -> None:
        """Clear all state."""
        self._symbol_state.clear()
