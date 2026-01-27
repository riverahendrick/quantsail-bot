"""Unit tests for Signal models."""

import pytest

from quantsail_engine.models.signal import Signal, SignalType


def test_signal_type_enum_values() -> None:
    """Test SignalType enum has expected values."""
    assert SignalType.HOLD == "HOLD"
    assert SignalType.ENTER_LONG == "ENTER_LONG"
    assert SignalType.EXIT == "EXIT"


def test_signal_creation_valid() -> None:
    """Test creating a valid signal."""
    signal = Signal(signal_type=SignalType.ENTER_LONG, symbol="BTC/USDT", confidence=0.85)
    assert signal.signal_type == SignalType.ENTER_LONG
    assert signal.symbol == "BTC/USDT"
    assert signal.confidence == 0.85


def test_signal_default_confidence() -> None:
    """Test signal uses default confidence of 1.0."""
    signal = Signal(signal_type=SignalType.HOLD, symbol="ETH/USDT")
    assert signal.confidence == 1.0


def test_signal_confidence_below_zero() -> None:
    """Test signal validation rejects confidence < 0.0."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        Signal(signal_type=SignalType.EXIT, symbol="BTC/USDT", confidence=-0.1)


def test_signal_confidence_above_one() -> None:
    """Test signal validation rejects confidence > 1.0."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        Signal(signal_type=SignalType.ENTER_LONG, symbol="BTC/USDT", confidence=1.5)


def test_signal_confidence_edge_zero() -> None:
    """Test signal allows confidence = 0.0."""
    signal = Signal(signal_type=SignalType.HOLD, symbol="BTC/USDT", confidence=0.0)
    assert signal.confidence == 0.0


def test_signal_confidence_edge_one() -> None:
    """Test signal allows confidence = 1.0."""
    signal = Signal(signal_type=SignalType.ENTER_LONG, symbol="BTC/USDT", confidence=1.0)
    assert signal.confidence == 1.0
