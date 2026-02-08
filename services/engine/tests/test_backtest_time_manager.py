"""Tests for TimeManager."""

from datetime import datetime, timezone

import pytest

from quantsail_engine.backtest.time_manager import TimeManager, generate_time_range


class TestTimeManager:
    """Test suite for TimeManager."""

    def test_initial_state(self) -> None:
        """Test initial state of time manager."""
        time_mgr = TimeManager()

        assert time_mgr._current_time is None
        assert time_mgr.get_start_time() is None
        assert time_mgr.get_end_time() is None

        with pytest.raises(RuntimeError, match="Time not set"):
            time_mgr.now()

    def test_set_time(self) -> None:
        """Test setting the current time."""
        time_mgr = TimeManager()
        ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        time_mgr.set_time(ts)

        assert time_mgr.now() == ts
        assert time_mgr.get_start_time() == ts

    def test_advance(self) -> None:
        """Test advancing time by seconds."""
        time_mgr = TimeManager()
        ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        time_mgr.set_time(ts)

        time_mgr.advance(300)  # 5 minutes

        expected = datetime(2024, 1, 1, 12, 5, tzinfo=timezone.utc)
        assert time_mgr.now() == expected

    def test_advance_minutes(self) -> None:
        """Test advancing time by minutes."""
        time_mgr = TimeManager()
        ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        time_mgr.set_time(ts)

        time_mgr.advance_minutes(30)

        expected = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)
        assert time_mgr.now() == expected

    def test_advance_to(self) -> None:
        """Test advancing to a specific timestamp."""
        time_mgr = TimeManager()
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        target = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
        time_mgr.set_time(start)

        time_mgr.advance_to(target)

        assert time_mgr.now() == target
        assert time_mgr.get_end_time() == target

    def test_advance_to_earlier_time_raises(self) -> None:
        """Test that advancing to earlier time raises error."""
        time_mgr = TimeManager()
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        earlier = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        time_mgr.set_time(start)

        with pytest.raises(ValueError, match="Cannot advance backwards"):
            time_mgr.advance_to(earlier)

    def test_advance_to_initializes_time(self) -> None:
        """Test that advance_to sets time if not set."""
        time_mgr = TimeManager()
        target = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        time_mgr.advance_to(target)

        assert time_mgr.now() == target
        assert time_mgr.get_start_time() == target

    def test_reset(self) -> None:
        """Test resetting time manager."""
        time_mgr = TimeManager()
        ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        time_mgr.set_time(ts)
        time_mgr.advance_minutes(60)

        time_mgr.reset()

        assert time_mgr._current_time is None
        assert time_mgr.get_start_time() is None
        assert time_mgr.get_end_time() is None

    def test_advance_without_set_time_raises(self) -> None:
        """Test that advancing without setting time raises error."""
        time_mgr = TimeManager()

        with pytest.raises(RuntimeError, match="Time not set"):
            time_mgr.advance(300)

        with pytest.raises(RuntimeError, match="Time not set"):
            time_mgr.advance_minutes(5)


class TestGenerateTimeRange:
    """Test suite for generate_time_range function."""

    def test_generate_hourly_range(self) -> None:
        """Test generating hourly timestamps."""
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc)

        timestamps = list(generate_time_range(start, end, interval_seconds=3600))

        assert len(timestamps) == 4  # 12:00, 13:00, 14:00, 15:00
        assert timestamps[0] == start
        assert timestamps[1] == datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        assert timestamps[-1] == end

    def test_generate_5min_range(self) -> None:
        """Test generating 5-minute timestamps."""
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 15, tzinfo=timezone.utc)

        timestamps = list(generate_time_range(start, end, interval_seconds=300))

        assert len(timestamps) == 4  # 12:00, 12:05, 12:10, 12:15
        assert timestamps[0] == start
        assert timestamps[-1] == end

    def test_single_timestamp(self) -> None:
        """Test when start equals end."""
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        timestamps = list(generate_time_range(start, end, interval_seconds=300))

        assert len(timestamps) == 1
        assert timestamps[0] == start

    def test_empty_range(self) -> None:
        """Test when end is before start."""
        start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)

        timestamps = list(generate_time_range(start, end, interval_seconds=300))

        # Should still yield start (the loop runs while current <= end)
        # Since start > end, loop doesn't run
        assert len(timestamps) == 0
