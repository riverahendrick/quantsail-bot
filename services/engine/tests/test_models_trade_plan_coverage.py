"""Additional tests for TradePlan edge cases and coverage."""

import pytest

from quantsail_engine.models.trade_plan import TradePlan


def test_trade_plan_unknown_side() -> None:
    """Test trade plan with unknown side (doesn't trigger validation)."""
    # Side validation is not enforced in __post_init__, only BUY is checked
    plan = TradePlan(
        symbol="BTC/USDT",
        side="SELL",  # Not validated for shorts in this implementation
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    # Should create successfully
    assert plan.side == "SELL"


def test_trade_plan_long_sl_equal_entry() -> None:
    """Test trade plan validation for SL == entry."""
    with pytest.raises(ValueError, match="Stop loss must be below entry"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=50000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_long_tp_equal_entry() -> None:
    """Test trade plan validation for TP == entry."""
    with pytest.raises(ValueError, match="Take profit must be above entry"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=50000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_stop_loss_price_negative() -> None:
    """Test trade plan validation rejects negative stop loss price."""
    with pytest.raises(ValueError, match="Stop loss price must be positive"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=-100.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_take_profit_price_negative() -> None:
    """Test trade plan validation rejects negative take profit price."""
    with pytest.raises(ValueError, match="Take profit price must be positive"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=-100.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )
