"""Losing streak position size reducer."""

import logging

from quantsail_engine.config.models import StreakSizerConfig

logger = logging.getLogger(__name__)


class StreakSizer:
    """Reduces position size after consecutive losses.

    After ``min_consecutive_losses`` consecutive losses on a symbol,
    the position multiplier is reduced by ``reduction_factor``.
    A win resets the streak to normal sizing (1.0).
    """

    def __init__(self, config: StreakSizerConfig) -> None:
        """Initialize StreakSizer.

        Args:
            config: Streak sizer configuration.
        """
        self.config = config
        # symbol -> consecutive_loss_count
        self._streaks: dict[str, int] = {}

    def record_result(self, symbol: str, won: bool) -> None:
        """Record a trade result.

        Args:
            symbol: Trading symbol.
            won: True if the trade was profitable.
        """
        if not self.config.enabled:
            return

        if won:
            if symbol in self._streaks:
                prev = self._streaks[symbol]
                self._streaks[symbol] = 0
                if prev >= self.config.min_consecutive_losses:
                    logger.info(
                        f"StreakSizer: {symbol} win resets sizing to 1.0x "
                        f"(was on {prev}-loss streak)"
                    )
        else:
            self._streaks[symbol] = self._streaks.get(symbol, 0) + 1
            streak = self._streaks[symbol]
            if streak >= self.config.min_consecutive_losses:
                logger.info(
                    f"StreakSizer: {symbol} at {streak} consecutive losses → "
                    f"{self.config.reduction_factor}x sizing"
                )

    def get_multiplier(self, symbol: str) -> float:
        """Get the position size multiplier for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Multiplier between 0.0 and 1.0 (1.0 = full size).
        """
        if not self.config.enabled:
            return 1.0

        streak = self._streaks.get(symbol, 0)
        if streak >= self.config.min_consecutive_losses:
            return self.config.reduction_factor

        return 1.0

    def reset(self) -> None:
        """Clear all streak state."""
        self._streaks.clear()
