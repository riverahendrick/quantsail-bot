"""API-side control plane accessor for bot lifecycle management.

Connects to the same Redis instance used by the engine to read/write
bot state (STOPPED, ARMED, RUNNING, PAUSED_ENTRIES).

If Redis is unavailable, falls back to an in-memory store (single-process only).
"""

import enum
import logging
import os
from functools import lru_cache
from typing import Protocol

logger = logging.getLogger(__name__)

_KEY_PREFIX = "quantsail:control"
_STATE_KEY = f"{_KEY_PREFIX}:state"
_LAST_HEARTBEAT_KEY = f"{_KEY_PREFIX}:heartbeat"


class BotState(str, enum.Enum):
    """Valid bot lifecycle states (mirrors engine BotState)."""

    STOPPED = "STOPPED"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    PAUSED_ENTRIES = "PAUSED_ENTRIES"


class ControlPlane(Protocol):
    """Protocol for bot control plane operations."""

    def get_state(self) -> BotState: ...
    def set_state(self, state: BotState) -> None: ...
    def get_last_heartbeat(self) -> float | None: ...


class RedisControlPlane:
    """Redis-backed control plane for cross-process coordination."""

    def __init__(self, redis_url: str) -> None:
        import redis as _redis

        self._client = _redis.Redis.from_url(redis_url, decode_responses=True)

    def get_state(self) -> BotState:
        try:
            raw = self._client.get(_STATE_KEY)
            if raw is None:
                return BotState.STOPPED
            return BotState(str(raw))
        except Exception as e:
            logger.error("Redis read failed, defaulting to STOPPED: %s", e)
            return BotState.STOPPED

    def set_state(self, state: BotState) -> None:
        self._client.set(_STATE_KEY, state.value)
        logger.info("Control plane state set to %s via API", state.value)

    def get_last_heartbeat(self) -> float | None:
        raw = self._client.get(_LAST_HEARTBEAT_KEY)
        if raw is None:
            return None
        return float(raw)


class InMemoryControlPlane:
    """In-memory fallback for testing / development."""

    def __init__(self) -> None:
        self._state = BotState.STOPPED

    def get_state(self) -> BotState:
        return self._state

    def set_state(self, state: BotState) -> None:
        self._state = state

    def get_last_heartbeat(self) -> float | None:
        return None


@lru_cache(maxsize=1)
def get_control_plane() -> ControlPlane:
    """Return the configured control plane singleton."""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            cp = RedisControlPlane(redis_url)
            # Test connectivity
            cp.get_state()
            logger.info("API control plane connected to Redis")
            return cp
        except Exception as e:
            logger.warning("Redis unavailable for control plane: %s — using InMemory", e)
    return InMemoryControlPlane()
