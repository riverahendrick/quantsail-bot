"""Tests for ProfitabilityGate."""

from quantsail_engine.gates.profitability import ProfitabilityGate
from quantsail_engine.models.trade_plan import TradePlan


def test_profitability_gate_pass() -> None:
    """Test gate passes when net profit exceeds minimum."""
    gate = ProfitabilityGate(min_profit_usd=1.0)
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,  # +200 USD gross
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    # Net = 200 - 5 - 2 - 1 = 192 USD (> 1.0)
    passed, net_profit = gate.evaluate(plan)
    assert passed is True
    assert net_profit == 192.0


def test_profitability_gate_fail() -> None:
    """Test gate fails when net profit below minimum."""
    gate = ProfitabilityGate(min_profit_usd=200.0)
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,  # +200 USD gross
        estimated_fee_usd=5.0,
        estimated_slippage_usd=2.0,
        estimated_spread_cost_usd=1.0,
    )
    # Net = 200 - 5 - 2 - 1 = 192 USD (< 200.0)
    passed, net_profit = gate.evaluate(plan)
    assert passed is False
    assert net_profit == 192.0


def test_profitability_gate_exact_minimum() -> None:
    """Test gate passes when net profit equals minimum."""
    gate = ProfitabilityGate(min_profit_usd=10.0)
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=50120.0,  # +12 USD gross
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
    )
    # Net = 12 - 1 - 0.5 - 0.5 = 10.0 USD (== 10.0)
    passed, net_profit = gate.evaluate(plan)
    assert passed is True
    assert net_profit == 10.0


def test_profitability_gate_negative_net_profit() -> None:
    """Test gate fails with negative net profit (costs exceed gross)."""
    gate = ProfitabilityGate(min_profit_usd=0.10)
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=50010.0,  # +1 USD gross
        estimated_fee_usd=2.0,
        estimated_slippage_usd=1.0,
        estimated_spread_cost_usd=0.5,
    )
    # Net = 1 - 2 - 1 - 0.5 = -2.5 USD
    passed, net_profit = gate.evaluate(plan)
    assert passed is False
    assert net_profit == -2.5


def test_profitability_gate_zero_minimum() -> None:
    """Test gate with zero minimum accepts any positive net profit."""
    gate = ProfitabilityGate(min_profit_usd=0.0)
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.1,
        stop_loss_price=49000.0,
        take_profit_price=50010.0,  # +1 USD gross
        estimated_fee_usd=0.5,
        estimated_slippage_usd=0.25,
        estimated_spread_cost_usd=0.25,
    )
    # Net = 1 - 0.5 - 0.25 - 0.25 = 0.0 USD
    passed, net_profit = gate.evaluate(plan)
    assert passed is True
    assert net_profit == 0.0
