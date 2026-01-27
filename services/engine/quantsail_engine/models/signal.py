"""Signal models for trading decisions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quantsail_engine.models.strategy import StrategyOutput


class SignalType(str, Enum):
    """Trading signal types."""

    HOLD = "HOLD"  # No action
    ENTER_LONG = "ENTER_LONG"  # Enter long position
    EXIT = "EXIT"  # Exit current position


@dataclass(frozen=True)
class Signal:
    """Trading signal with metadata."""

    signal_type: SignalType
    symbol: str
    confidence: float = 1.0  # 0.0 to 1.0
    strategy_outputs: list["StrategyOutput"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate signal data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

