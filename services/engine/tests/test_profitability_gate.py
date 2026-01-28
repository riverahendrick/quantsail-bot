"""Unit tests for Profitability Gate."""

import pytest
from datetime import datetime, timezone
from quantsail_engine.gates.profitability import ProfitabilityGate
from quantsail_engine.models.trade_plan import TradePlan


def test_profitability_gate_pass() -> None:
    gate = ProfitabilityGate(min_profit_usd=1.0)
    
    # Entry 100, TP 105, Qty 1.0. Gross 5.0.
    # Costs: Fee 1.0, Slip 0.5, Spread 0.5 -> Total 2.0.
    # Net: 3.0.
    
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss_price=95.0,
        take_profit_price=105.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="test-1",
        timestamp=datetime.now(timezone.utc),
    )
    
    passed, breakdown = gate.evaluate(plan)
    assert passed is True
    assert breakdown["net_profit_usd"] == 3.0
    assert breakdown["gross_profit_usd"] == 5.0
    assert breakdown["passed"] is True


def test_profitability_gate_fail() -> None:
    gate = ProfitabilityGate(min_profit_usd=5.0)
    
    # Same plan, Net 3.0 < 5.0
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss_price=95.0,
        take_profit_price=105.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="test-2",
        timestamp=datetime.now(timezone.utc),
    )
    
    passed, breakdown = gate.evaluate(plan)
    assert passed is False
    assert breakdown["net_profit_usd"] == 3.0
    assert breakdown["passed"] is False


def test_profitability_gate_negative_net() -> None:
    gate = ProfitabilityGate(min_profit_usd=0.0)
    
    # Gross 1.0 (TP 101). Costs 2.0. Net -1.0.
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss_price=95.0,
        take_profit_price=101.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="test-3",
        timestamp=datetime.now(timezone.utc),
    )
    
    passed, breakdown = gate.evaluate(plan)
    assert passed is False
    assert breakdown["net_profit_usd"] == -1.0
