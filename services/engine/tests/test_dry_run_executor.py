"""Tests for DryRunExecutor."""

from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.models.trade_plan import TradePlan


def test_execute_entry_creates_trade_and_orders() -> None:
    """Test execute_entry creates trade with 3 orders."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)

    assert "trade" in result
    assert "orders" in result
    assert len(result["orders"]) == 3  # Entry, SL, TP


def test_execute_entry_trade_properties() -> None:
    """Test execute_entry trade has correct properties."""
    executor = DryRunExecutor()
    plan = TradePlan(
        symbol="ETH/USDT",
        side="BUY",
        entry_price=3000.0,
        quantity=1.0,
        stop_loss_price=2900.0,
        take_profit_price=3200.0,
        estimated_fee_usd=3.0,
        estimated_slippage_usd=1.0,
        estimated_spread_cost_usd=0.5,
    )

    result = executor.execute_entry(plan)
    trade = result["trade"]

    assert trade["symbol"] == "ETH/USDT"
    assert trade["mode"] == "DRY_RUN"
    assert trade["status"] == "OPEN"
    assert trade["side"] == "BUY"
    assert trade["entry_price"] == 3000.0
    assert trade["quantity"] == 1.0
    assert trade["pnl_usd"] is None  # Not closed yet


def test_execute_entry_order_types() -> None:
    """Test execute_entry creates correct order types."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    orders = result["orders"]

    entry_order = orders[0]
    sl_order = orders[1]
    tp_order = orders[2]

    assert entry_order["order_type"] == "MARKET"
    assert entry_order["status"] == "FILLED"
    assert sl_order["order_type"] == "STOP_LOSS"
    assert sl_order["status"] == "PENDING"
    assert tp_order["order_type"] == "TAKE_PROFIT"
    assert tp_order["status"] == "PENDING"


def test_check_exits_no_trigger() -> None:
    """Test check_exits returns None when no exit triggered."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    trade_id = result["trade"]["id"]

    # Price between SL and TP
    exit_result = executor.check_exits(trade_id, 50500.0)
    assert exit_result is None


def test_check_exits_stop_loss_hit() -> None:
    """Test check_exits detects SL hit for long position."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    trade_id = result["trade"]["id"]

    # Price at or below SL
    exit_result = executor.check_exits(trade_id, 49000.0)
    assert exit_result is not None
    assert exit_result["exit_reason"] == "STOP_LOSS"
    assert exit_result["trade"]["status"] == "CLOSED"
    assert exit_result["trade"]["exit_price"] == 49000.0


def test_check_exits_take_profit_hit() -> None:
    """Test check_exits detects TP hit for long position."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    trade_id = result["trade"]["id"]

    # Price at or above TP
    exit_result = executor.check_exits(trade_id, 52000.0)
    assert exit_result is not None
    assert exit_result["exit_reason"] == "TAKE_PROFIT"
    assert exit_result["trade"]["status"] == "CLOSED"
    assert exit_result["trade"]["exit_price"] == 52000.0


def test_check_exits_pnl_calculation() -> None:
    """Test check_exits calculates PnL correctly."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    trade_id = result["trade"]["id"]

    # TP hit: (52000 - 50000) * 0.1 = +200 USD
    exit_result = executor.check_exits(trade_id, 52000.0)
    assert exit_result is not None
    assert exit_result["trade"]["pnl_usd"] == 200.0
    assert exit_result["trade"]["pnl_pct"] == 4.0  # 200 / 5000 * 100


def test_check_exits_removes_from_open_trades() -> None:
    """Test check_exits removes trade after exit."""
    executor = DryRunExecutor()
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

    result = executor.execute_entry(plan)
    trade_id = result["trade"]["id"]

    # Exit the trade
    executor.check_exits(trade_id, 52000.0)

    # Second check should return None (trade no longer open)
    exit_result = executor.check_exits(trade_id, 52000.0)
    assert exit_result is None


def test_check_exits_nonexistent_trade() -> None:
    """Test check_exits returns None for nonexistent trade."""
    executor = DryRunExecutor()
    exit_result = executor.check_exits("nonexistent-id", 50000.0)
    assert exit_result is None
