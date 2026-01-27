"""Unit tests for StateMachine."""

import pytest

from quantsail_engine.core.state_machine import StateMachine, TradingState


def test_state_machine_init_default() -> None:
    """Test state machine initializes to IDLE by default."""
    sm = StateMachine("BTC/USDT")
    assert sm.symbol == "BTC/USDT"
    assert sm.current_state == TradingState.IDLE


def test_state_machine_init_custom_state() -> None:
    """Test state machine can initialize to a custom state."""
    sm = StateMachine("ETH/USDT", TradingState.IN_POSITION)
    assert sm.current_state == TradingState.IN_POSITION


def test_transition_idle_to_eval() -> None:
    """Test valid transition from IDLE to EVAL."""
    sm = StateMachine("BTC/USDT")
    sm.transition_to(TradingState.EVAL)
    assert sm.current_state == TradingState.EVAL


def test_transition_eval_to_idle() -> None:
    """Test valid transition from EVAL to IDLE."""
    sm = StateMachine("BTC/USDT", TradingState.EVAL)
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE


def test_transition_eval_to_entry_pending() -> None:
    """Test valid transition from EVAL to ENTRY_PENDING."""
    sm = StateMachine("BTC/USDT", TradingState.EVAL)
    sm.transition_to(TradingState.ENTRY_PENDING)
    assert sm.current_state == TradingState.ENTRY_PENDING


def test_transition_entry_pending_to_in_position() -> None:
    """Test valid transition from ENTRY_PENDING to IN_POSITION."""
    sm = StateMachine("BTC/USDT", TradingState.ENTRY_PENDING)
    sm.transition_to(TradingState.IN_POSITION)
    assert sm.current_state == TradingState.IN_POSITION


def test_transition_entry_pending_to_idle() -> None:
    """Test valid transition from ENTRY_PENDING to IDLE (failed entry)."""
    sm = StateMachine("BTC/USDT", TradingState.ENTRY_PENDING)
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE


def test_transition_in_position_to_exit_pending() -> None:
    """Test valid transition from IN_POSITION to EXIT_PENDING."""
    sm = StateMachine("BTC/USDT", TradingState.IN_POSITION)
    sm.transition_to(TradingState.EXIT_PENDING)
    assert sm.current_state == TradingState.EXIT_PENDING


def test_transition_exit_pending_to_idle() -> None:
    """Test valid transition from EXIT_PENDING to IDLE."""
    sm = StateMachine("BTC/USDT", TradingState.EXIT_PENDING)
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE


def test_invalid_transition_idle_to_in_position() -> None:
    """Test invalid transition from IDLE to IN_POSITION."""
    sm = StateMachine("BTC/USDT")
    with pytest.raises(ValueError, match="Invalid transition from TradingState.IDLE"):
        sm.transition_to(TradingState.IN_POSITION)


def test_invalid_transition_eval_to_in_position() -> None:
    """Test invalid transition from EVAL to IN_POSITION."""
    sm = StateMachine("BTC/USDT", TradingState.EVAL)
    with pytest.raises(ValueError, match="Invalid transition from TradingState.EVAL"):
        sm.transition_to(TradingState.IN_POSITION)


def test_invalid_transition_in_position_to_idle() -> None:
    """Test invalid transition from IN_POSITION to IDLE."""
    sm = StateMachine("BTC/USDT", TradingState.IN_POSITION)
    with pytest.raises(ValueError, match="Invalid transition from TradingState.IN_POSITION"):
        sm.transition_to(TradingState.IDLE)


def test_invalid_transition_exit_pending_to_in_position() -> None:
    """Test invalid transition from EXIT_PENDING to IN_POSITION."""
    sm = StateMachine("BTC/USDT", TradingState.EXIT_PENDING)
    with pytest.raises(ValueError, match="Invalid transition from TradingState.EXIT_PENDING"):
        sm.transition_to(TradingState.IN_POSITION)


def test_can_transition_to_valid() -> None:
    """Test can_transition_to returns True for valid transitions."""
    sm = StateMachine("BTC/USDT", TradingState.EVAL)
    assert sm.can_transition_to(TradingState.IDLE) is True
    assert sm.can_transition_to(TradingState.ENTRY_PENDING) is True


def test_can_transition_to_invalid() -> None:
    """Test can_transition_to returns False for invalid transitions."""
    sm = StateMachine("BTC/USDT", TradingState.IDLE)
    assert sm.can_transition_to(TradingState.IN_POSITION) is False
    assert sm.can_transition_to(TradingState.EXIT_PENDING) is False


def test_reset() -> None:
    """Test reset returns state machine to IDLE."""
    sm = StateMachine("BTC/USDT", TradingState.IN_POSITION)
    sm.reset()
    assert sm.current_state == TradingState.IDLE


def test_full_trade_lifecycle() -> None:
    """Test complete trade lifecycle transitions."""
    sm = StateMachine("BTC/USDT")

    # IDLE -> EVAL
    sm.transition_to(TradingState.EVAL)
    assert sm.current_state == TradingState.EVAL

    # EVAL -> ENTRY_PENDING
    sm.transition_to(TradingState.ENTRY_PENDING)
    assert sm.current_state == TradingState.ENTRY_PENDING

    # ENTRY_PENDING -> IN_POSITION
    sm.transition_to(TradingState.IN_POSITION)
    assert sm.current_state == TradingState.IN_POSITION

    # IN_POSITION -> EXIT_PENDING
    sm.transition_to(TradingState.EXIT_PENDING)
    assert sm.current_state == TradingState.EXIT_PENDING

    # EXIT_PENDING -> IDLE
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE


def test_eval_no_signal_lifecycle() -> None:
    """Test lifecycle when EVAL returns to IDLE (no signal)."""
    sm = StateMachine("BTC/USDT")

    # IDLE -> EVAL
    sm.transition_to(TradingState.EVAL)
    assert sm.current_state == TradingState.EVAL

    # EVAL -> IDLE (no entry signal)
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE


def test_failed_entry_lifecycle() -> None:
    """Test lifecycle when entry fails."""
    sm = StateMachine("BTC/USDT")

    # IDLE -> EVAL -> ENTRY_PENDING
    sm.transition_to(TradingState.EVAL)
    sm.transition_to(TradingState.ENTRY_PENDING)
    assert sm.current_state == TradingState.ENTRY_PENDING

    # ENTRY_PENDING -> IDLE (failed entry)
    sm.transition_to(TradingState.IDLE)
    assert sm.current_state == TradingState.IDLE
