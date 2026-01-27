"""Data models for circuit breaker system."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ActiveBreaker:
    """Represents an active circuit breaker."""

    breaker_type: str
    triggered_at: datetime
    expires_at: datetime
    reason: str
    context: dict[str, float]
