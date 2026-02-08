"""Simulated time manager for backtesting.

Provides deterministic time control so that all engine components
see a consistent "current time" during backtest execution.
"""

from datetime import datetime, timezone
from typing import Iterator


class TimeManager:
    """Manages simulated time during backtesting.

    This class provides a centralized time source that advances
    through historical data timestamps. All components that need
    to know the "current time" should query this manager.

    Example:
        >>> time_mgr = TimeManager()
        >>> time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        >>> print(time_mgr.now())  # 2024-01-01 12:00:00+00:00
        >>> time_mgr.advance_minutes(5)
        >>> print(time_mgr.now())  # 2024-01-01 12:05:00+00:00
    """

    def __init__(self) -> None:
        """Initialize time manager with no current time set."""
        self._current_time: datetime | None = None
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None

    def set_time(self, timestamp: datetime) -> None:
        """Set the current simulated time.

        Args:
            timestamp: The current simulated timestamp
        """
        self._current_time = timestamp
        if self._start_time is None:
            self._start_time = timestamp

    def now(self) -> datetime:
        """Get the current simulated time.

        Returns:
            Current simulated timestamp

        Raises:
            RuntimeError: If time has not been set
        """
        if self._current_time is None:
            raise RuntimeError("Time not set. Call set_time() first.")
        return self._current_time

    def advance(self, delta_seconds: int) -> None:
        """Advance time by a number of seconds.

        Args:
            delta_seconds: Number of seconds to advance
        """
        if self._current_time is None:
            raise RuntimeError("Time not set. Call set_time() first.")
        self._current_time = self._current_time.fromtimestamp(
            self._current_time.timestamp() + delta_seconds,
            tz=timezone.utc,
        )

    def advance_minutes(self, minutes: int) -> None:
        """Advance time by a number of minutes.

        Args:
            minutes: Number of minutes to advance
        """
        self.advance(minutes * 60)

    def advance_to(self, timestamp: datetime) -> None:
        """Advance time to a specific timestamp.

        Args:
            timestamp: Target timestamp (must be >= current time)

        Raises:
            ValueError: If timestamp is before current time
        """
        if self._current_time is None:
            self.set_time(timestamp)
            return

        if timestamp < self._current_time:
            raise ValueError(
                f"Cannot advance backwards: {timestamp} < {self._current_time}"
            )
        self._current_time = timestamp
        self._end_time = timestamp

    def get_start_time(self) -> datetime | None:
        """Get the simulation start time.

        Returns:
            Start timestamp or None if not set
        """
        return self._start_time

    def get_end_time(self) -> datetime | None:
        """Get the simulation end time.

        Returns:
            End timestamp or None if not set
        """
        return self._end_time

    def reset(self) -> None:
        """Reset time manager to initial state."""
        self._current_time = None
        self._start_time = None
        self._end_time = None


def generate_time_range(
    start: datetime,
    end: datetime,
    interval_seconds: int = 300,  # 5 minutes default
) -> Iterator[datetime]:
    """Generate a range of timestamps at regular intervals.

    Args:
        start: Start timestamp
        end: End timestamp
        interval_seconds: Interval between timestamps (default: 300s = 5min)

    Yields:
        Timestamps from start to end at specified intervals
    """
    current = start
    while current <= end:
        yield current
        current = datetime.fromtimestamp(
            current.timestamp() + interval_seconds,
            tz=timezone.utc,
        )
