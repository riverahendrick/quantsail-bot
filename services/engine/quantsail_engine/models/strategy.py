"""Strategy-related data models."""

from dataclasses import dataclass, field
from typing import Any

from quantsail_engine.models.signal import SignalType


@dataclass(frozen=True)
class StrategyOutput:
    """Standard output format for all strategies."""

    signal: SignalType
    confidence: float
    strategy_name: str
    rationale: dict[str, Any] = field(default_factory=dict)
