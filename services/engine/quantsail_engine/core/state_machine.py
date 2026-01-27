"""Trading state machine with validated transitions."""

from enum import Enum


class TradingState(str, Enum):
    """Trading states for the per-symbol state machine."""

    IDLE = "IDLE"  # No position, no pending orders
    EVAL = "EVAL"  # Evaluating market data and generating signals
    ENTRY_PENDING = "ENTRY_PENDING"  # Entry order being placed
    IN_POSITION = "IN_POSITION"  # Position open, monitoring for exits
    EXIT_PENDING = "EXIT_PENDING"  # Exit order being placed


# Valid state transitions
VALID_TRANSITIONS: dict[TradingState, list[TradingState]] = {
    TradingState.IDLE: [TradingState.EVAL],
    TradingState.EVAL: [TradingState.IDLE, TradingState.ENTRY_PENDING],
    TradingState.ENTRY_PENDING: [TradingState.IN_POSITION, TradingState.IDLE],
    TradingState.IN_POSITION: [TradingState.EXIT_PENDING],
    TradingState.EXIT_PENDING: [TradingState.IDLE],
}


class StateMachine:
    """Per-symbol trading state machine with transition validation."""

    def __init__(self, symbol: str, initial_state: TradingState = TradingState.IDLE):
        """
        Initialize state machine.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            initial_state: Starting state (default: IDLE)
        """
        self.symbol = symbol
        self._current_state = initial_state

    @property
    def current_state(self) -> TradingState:
        """Get current state."""
        return self._current_state

    def transition_to(self, new_state: TradingState) -> None:
        """
        Transition to a new state with validation.

        Args:
            new_state: Target state

        Raises:
            ValueError: If transition is invalid
        """
        if new_state not in VALID_TRANSITIONS[self._current_state]:
            raise ValueError(
                f"Invalid transition from {self._current_state} to {new_state} "
                f"for {self.symbol}"
            )

        self._current_state = new_state

    def can_transition_to(self, new_state: TradingState) -> bool:
        """
        Check if transition is valid without executing it.

        Args:
            new_state: Target state

        Returns:
            True if transition is allowed
        """
        return new_state in VALID_TRANSITIONS[self._current_state]

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self._current_state = TradingState.IDLE
