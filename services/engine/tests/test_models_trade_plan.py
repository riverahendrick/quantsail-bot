"""Unit tests for TradePlan model."""

import pytest

from quantsail_engine.models.trade_plan import TradePlan


def test_trade_plan_creation_valid_long() -> None:
    """Test creating a valid long trade plan."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    assert plan.symbol == "BTC/USDT"
    assert plan.side == "BUY"
    assert plan.entry_price == 50000.0
    assert plan.quantity == 0.1


def test_trade_plan_entry_price_zero() -> None:
    """Test trade plan validation rejects zero entry price."""
    with pytest.raises(ValueError, match="Entry price must be positive"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=0.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_entry_price_negative() -> None:
    """Test trade plan validation rejects negative entry price."""
    with pytest.raises(ValueError, match="Entry price must be positive"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=-50000.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_quantity_zero() -> None:
    """Test trade plan validation rejects zero quantity."""
    with pytest.raises(ValueError, match="Quantity must be positive"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.0,
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_long_sl_above_entry() -> None:
    """Test trade plan validation rejects SL >= entry for long."""
    with pytest.raises(ValueError, match="Stop loss must be below entry"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=50000.0,  # SL >= entry, invalid
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_long_tp_below_entry() -> None:
    """Test trade plan validation rejects TP <= entry for long."""
    with pytest.raises(ValueError, match="Take profit must be above entry"):
        TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=50000.0,  # TP <= entry, invalid
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.0,
            estimated_spread_cost_usd=1.0,
        )


def test_trade_plan_position_value_usd() -> None:
    """Test trade plan position_value_usd calculation."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    assert plan.position_value_usd == 5000.0  # 50000 * 0.1


def test_trade_plan_risk_usd() -> None:
    """Test trade plan risk_usd calculation."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    assert plan.risk_usd == 100.0  # (50000 - 49000) * 0.1


def test_trade_plan_reward_usd() -> None:
    """Test trade plan reward_usd calculation."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    assert plan.reward_usd == 200.0  # (52000 - 50000) * 0.1


def test_trade_plan_risk_reward_ratio() -> None:
    """Test trade plan risk_reward_ratio calculation."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    assert plan.risk_reward_ratio == 2.0  # 200 / 100


def test_trade_plan_risk_reward_ratio_zero_risk() -> None:
    """Test trade plan risk_reward_ratio with zero risk (edge case)."""
    # This shouldn't happen in practice due to validation, but test behavior
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49999.99,  # Tiny risk
        take_profit_price=52000.0,
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    # Should not raise, returns ratio
    assert plan.risk_reward_ratio > 0
