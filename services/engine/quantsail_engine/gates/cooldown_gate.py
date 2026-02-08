"""Stop-loss cooldown gate — blocks re-entry after a stop-loss exit."""

import logging
from datetime import datetime, timedelta

from quantsail_engine.config.models import CooldownConfig

logger = logging.getLogger(__name__)


class CooldownGate:
    """Blocks re-entry for a symbol after a stop-loss exit.

    Prevents cluster losses caused by immediate re-entry into a
    still-unfavorable market after being stopped out.
    """

    def __init__(self, config: CooldownConfig) -> None:
        """Initialize CooldownGate.

        Args:
            config: Cooldown configuration.
        """
        self.config = config
        self._last_sl_exit: dict[str, datetime] = {}

    def record_exit(
        self, symbol: str, exit_reason: str, timestamp: datetime
    ) -> None:
        """Record a trade exit, tracking stop-loss exits for cooldown.

        Args:
            symbol: Trading symbol.
            exit_reason: Reason for exit (e.g. "stop_loss", "take_profit").
            timestamp: Time of the exit.
        """
        if not self.config.enabled:
            return

        if exit_reason == "stop_loss":
            self._last_sl_exit[symbol] = timestamp
            logger.info(
                f"Cooldown started for {symbol} — "
                f"blocked until {timestamp + timedelta(minutes=self.config.cooldown_minutes)}"
            )

    def is_allowed(
        self, symbol: str, current_time: datetime
    ) -> tuple[bool, str | None]:
        """Check if trading is allowed for the symbol (cooldown expired).

        Args:
            symbol: Trading symbol.
            current_time: Current simulation or wall-clock time.

        Returns:
            Tuple of (allowed, rejection_reason).
        """
        if not self.config.enabled:
            return True, None

        last_sl = self._last_sl_exit.get(symbol)
        if last_sl is None:
            return True, None

        cooldown_end = last_sl + timedelta(minutes=self.config.cooldown_minutes)
        if current_time < cooldown_end:
            remaining = cooldown_end - current_time
            reason = (
                f"stop_loss_cooldown_active "
                f"(remaining={remaining.total_seconds() / 60:.0f}min)"
            )
            return False, reason

        return True, None

    def reset(self) -> None:
        """Clear all cooldown state (e.g. on new backtest run)."""
        self._last_sl_exit.clear()
