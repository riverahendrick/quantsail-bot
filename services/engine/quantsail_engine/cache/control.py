"""Redis-backed control plane for the trading engine.

Manages bot lifecycle states (STOPPED, ARMED, RUNNING, PAUSED_ENTRIES)
via Redis for cross-process coordination between the API and engine.

If Redis is unavailable, defaults to safe mode (STOPPED — no new entries,
exits still active) to protect capital.
"""

import enum
import logging
import time
from typing import Protocol, cast, runtime_checkable

logger = logging.getLogger(__name__)

# Redis key namespace
_KEY_PREFIX = "quantsail:control"
_STATE_KEY = f"{_KEY_PREFIX}:state"
_ARMED_AT_KEY = f"{_KEY_PREFIX}:armed_at"
_ARMING_TOKEN_KEY = f"{_KEY_PREFIX}:arming_token"
_LAST_HEARTBEAT_KEY = f"{_KEY_PREFIX}:heartbeat"


class BotState(str, enum.Enum):
    """Valid bot lifecycle states."""

    STOPPED = "STOPPED"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    PAUSED_ENTRIES = "PAUSED_ENTRIES"


@runtime_checkable
class ControlPlane(Protocol):
    """Protocol for bot control plane implementations."""

    def get_state(self) -> BotState:
        """Return the current desired bot state."""
        ...

    def set_state(self, state: BotState) -> None:
        """Set the desired bot state."""
        ...

    def is_entries_allowed(self) -> bool:
        """Return True if the bot should accept new entries."""
        ...

    def is_exits_allowed(self) -> bool:
        """Return True if the bot should process exits."""
        ...

    def heartbeat(self) -> None:
        """Record a heartbeat from the engine."""
        ...


class RedisControlPlane:
    """Control plane backed by Redis.

    Both the API and the engine connect to the same Redis instance.
    State changes made via the API are immediately visible to the engine.
    """

    def __init__(self, redis_client: object) -> None:
        """Initialize with a Redis client.

        Args:
            redis_client: A connected redis.Redis (or compatible) instance.
        """
        self._redis = redis_client

    def get_state(self) -> BotState:
        """Read current state from Redis. Defaults to STOPPED if not set."""
        try:
            raw = self._redis.get(_STATE_KEY)  # type: ignore[union-attr]
            if raw is None:
                return BotState.STOPPED
            value = raw.decode() if isinstance(raw, bytes) else str(raw)
            return cast(BotState, BotState(value))
        except Exception as e:
            logger.error("Redis read failed, defaulting to STOPPED: %s", e)
            return BotState.STOPPED

    def set_state(self, state: BotState) -> None:
        """Write state to Redis."""
        try:
            self._redis.set(_STATE_KEY, state.value)  # type: ignore[union-attr]
            logger.info("Control plane state set to %s", state.value)
        except Exception as e:
            logger.error("Failed to set control state: %s", e)
            raise

    def is_entries_allowed(self) -> bool:
        """Entries allowed only in RUNNING state."""
        return self.get_state() == BotState.RUNNING

    def is_exits_allowed(self) -> bool:
        """Exits allowed in RUNNING, PAUSED_ENTRIES, and ARMED states.

        Even when paused or armed, we must still monitor and execute
        exits on existing positions to protect capital.
        """
        state = self.get_state()
        return state in (BotState.RUNNING, BotState.PAUSED_ENTRIES, BotState.ARMED)

    def heartbeat(self) -> None:
        """Write engine heartbeat timestamp."""
        try:
            self._redis.set(  # type: ignore[union-attr]
                _LAST_HEARTBEAT_KEY,
                str(int(time.time())),
            )
        except Exception as e:
            logger.warning("Heartbeat write failed: %s", e)


class InMemoryControlPlane:
    """In-memory control plane for testing and dry-run.

    Not suitable for production where API and engine are separate processes.
    """

    def __init__(self, initial_state: BotState = BotState.STOPPED) -> None:
        self._state = initial_state
        self._last_heartbeat: float = 0.0

    def get_state(self) -> BotState:
        return self._state

    def set_state(self, state: BotState) -> None:
        self._state = state

    def is_entries_allowed(self) -> bool:
        return self._state == BotState.RUNNING

    def is_exits_allowed(self) -> bool:
        return self._state in (BotState.RUNNING, BotState.PAUSED_ENTRIES, BotState.ARMED)

    def heartbeat(self) -> None:
        self._last_heartbeat = time.time()


def get_control_plane(redis_url: str | None = None) -> ControlPlane:
    """Factory: return Redis-backed control plane if URL provided, else in-memory.

    Args:
        redis_url: Redis connection URL (e.g. ``redis://localhost:6379/0``).

    Returns:
        A ControlPlane implementation.
    """
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=False)
            client.ping()
            logger.info("Control plane connected to Redis at %s", redis_url)
            return RedisControlPlane(client)
        except Exception as e:
            logger.error(
                "Failed to connect to Redis (%s): %s — falling back to InMemory",
                redis_url, e,
            )

    logger.info("Control plane: InMemory (single-process only)")
    return InMemoryControlPlane()
