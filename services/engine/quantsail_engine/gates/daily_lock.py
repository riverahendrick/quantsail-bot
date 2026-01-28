"""Daily target lock manager."""

from quantsail_engine.config.models import DailyConfig
from quantsail_engine.persistence.repository import EngineRepository


class DailyLockManager:
    """Manages daily profit target lock (STOP/OVERDRIVE)."""

    def __init__(self, config: DailyConfig, repo: EngineRepository):
        """
        Initialize DailyLockManager.

        Args:
            config: Daily configuration
            repo: Engine repository
        """
        self.config = config
        self.repo = repo

        # State
        self.target_reached = False
        self.entries_paused = False
        self.peak_realized_pnl = 0.0
        self.floor_usd = 0.0

        # Used to track if we need to emit floor_updated
        self._last_emitted_floor = 0.0

        # Optimization: Don't reconstruct on every tick
        self._peak_initialized = False

    def entries_allowed(self) -> tuple[bool, str | None]:
        """
        Check if entries are allowed based on daily PnL.

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.config.enabled:
            return True, None

        current_pnl = self.repo.get_today_realized_pnl(self.config.timezone)

        # Initialize/Update State
        self._update_state(current_pnl)

        if self.entries_paused:
            if self.config.mode == "STOP":
                return (
                    False,
                    f"Daily target reached (STOP mode). PnL: ${current_pnl:.2f}",
                )
            else:
                return (
                    False,
                    f"Overdrive profit floor breached. "
                    f"PnL: ${current_pnl:.2f} < Floor: ${self.floor_usd:.2f}",
                )

        return True, None

    def _update_state(self, current_pnl: float) -> None:
        """Update internal state based on current PnL."""
        # 1. Check if we hit target for the first time
        if not self.target_reached and current_pnl >= self.config.target_usd:
            self.target_reached = True
            self.repo.append_event(
                event_type="daily_lock.engaged",
                level="INFO",
                payload={
                    "mode": self.config.mode,
                    "realized_pnl": current_pnl,
                    "target_usd": self.config.target_usd,
                },
                public_safe=True,
            )

            # If STOP mode, pause immediately
            if self.config.mode == "STOP":
                self.entries_paused = True
                return

        # 2. OVERDRIVE Logic
        if self.config.mode == "OVERDRIVE":
            if not self._peak_initialized:
                self._reconstruct_peak(current_pnl)
                self._peak_initialized = True

            # Update Peak
            if current_pnl > self.peak_realized_pnl:
                self.peak_realized_pnl = current_pnl

                # Update Floor
                # Floor = max(target, peak - buffer)
                new_floor = max(
                    self.config.target_usd,
                    self.peak_realized_pnl - self.config.overdrive_trailing_buffer_usd,
                )

                if new_floor > self.floor_usd:
                    self.floor_usd = new_floor
                    # Emit floor updated if changed significantly
                    if self.floor_usd > self._last_emitted_floor:
                        self.repo.append_event(
                            event_type="daily_lock.floor_updated",
                            level="INFO",
                            payload={
                                "peak_pnl": self.peak_realized_pnl,
                                "new_floor": self.floor_usd,
                                "current_pnl": current_pnl,
                            },
                            public_safe=True,
                        )
                        self._last_emitted_floor = self.floor_usd

            # Check Floor Breach
            # Only enforces if we are "in overdrive" (target reached)
            if self.target_reached and not self.entries_paused:
                if current_pnl < self.floor_usd:
                    self.entries_paused = True
                    self.repo.append_event(
                        event_type="daily_lock.entries_paused",
                        level="WARN",
                        payload={
                            "reason": "Overdrive floor breached",
                            "current_pnl": current_pnl,
                            "floor_usd": self.floor_usd,
                            "peak_pnl": self.peak_realized_pnl,
                        },
                        public_safe=True,
                    )

    def _reconstruct_peak(self, current_pnl: float) -> None:
        """Reconstruct peak PnL from today's trade history if needed."""
        # Initialize with current
        self.peak_realized_pnl = current_pnl

        # Query trades to see if we were higher
        trades = self.repo.get_today_closed_trades(self.config.timezone)

        running_pnl = 0.0
        max_pnl = 0.0  # Assumes we start at 0 for "Realized PnL Today"

        # If we have no trades, max is 0.
        # If we have trades, we simulate the curve.

        for trade in trades:
            running_pnl += float(trade.realized_pnl_usd or 0.0)
            if running_pnl > max_pnl:
                max_pnl = running_pnl

        if max_pnl > self.peak_realized_pnl:
            self.peak_realized_pnl = max_pnl

        # Update target_reached if peak >= target
        if self.peak_realized_pnl >= self.config.target_usd:
            self.target_reached = True

        # Initial floor calc
        self.floor_usd = max(
            self.config.target_usd,
            self.peak_realized_pnl - self.config.overdrive_trailing_buffer_usd,
        )
