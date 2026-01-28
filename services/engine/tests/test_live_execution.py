"""Tests for LiveExecutor and Idempotency."""

from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime

from quantsail_engine.execution.live_executor import LiveExecutor
from quantsail_engine.models.trade_plan import TradePlan


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    # Default: trade not found
    repo.get_trade.return_value = None
    return repo


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    return adapter


@pytest.fixture
def executor(mock_repo, mock_adapter):
    return LiveExecutor(mock_repo, mock_adapter)


def test_execute_entry_success(executor, mock_repo, mock_adapter):
    """Test successful live order placement."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.01,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="uuid-123",
        timestamp=datetime.utcnow()
    )

    # Mock exchange response
    mock_adapter.create_order.return_value = {
        "id": "exchange-order-999",
        "price": 50005.0,
        "average": 50006.0,
        "amount": 0.01,
        "datetime": "2024-01-01T12:00:00Z"
    }

    result = executor.execute_entry(plan)

    assert result is not None
    trade = result["trade"]
    orders = result["orders"]
    assert trade["id"] == "uuid-123"
    assert orders[0]["exchange_order_id"] == "exchange-order-999"
    
    # Verify idempotency key was used
    mock_adapter.create_order.assert_called_once()
    call_args = mock_adapter.create_order.call_args
    assert call_args.kwargs["client_order_id"] == "QS-uuid-123-ENTRY"
    
    assert trade["entry_price"] == 50006.0  # From average fill


def test_execute_entry_idempotency_hit(executor, mock_repo, mock_adapter):
    """Test that existing trade prevents duplicate order."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.01,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="uuid-123",
        timestamp=datetime.utcnow()
    )

    # Simulate trade already exists
    mock_repo.get_trade.return_value = {"id": "uuid-123", "status": "OPEN"}

    result = executor.execute_entry(plan)

    assert result is not None
    assert result["trade"]["id"] == "uuid-123"
    assert result["orders"] == []
    
    # Verify exchange was NOT called
    mock_adapter.create_order.assert_not_called()
    mock_repo.append_event.assert_called_with(
        event_type="execution.idempotency_hit",
        level="WARN",
        payload={"trade_id": "uuid-123"},
        public_safe=False
    )


def test_execute_entry_failure(executor, mock_repo, mock_adapter):
    """Test handling of exchange errors."""
    plan = TradePlan(
        symbol="BTC/USDT",
        side="BUY",
        entry_price=50000.0,
        quantity=0.01,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        estimated_fee_usd=1.0,
        estimated_slippage_usd=0.5,
        estimated_spread_cost_usd=0.5,
        trade_id="uuid-123",
        timestamp=datetime.utcnow()
    )

    # Mock failure
    mock_adapter.create_order.side_effect = Exception("API Error")

    trade_id = executor.execute_entry(plan)

    assert trade_id is None
    
    # Verify error logged
    mock_repo.append_event.assert_called_with(
        event_type="error.execution",
        level="ERROR",
        payload={"error": "API Error", "trade_id": "uuid-123"},
        public_safe=False
    )


def test_reconcile_state(executor, mock_repo, mock_adapter):
    """Test reconciliation logic."""
    # Setup open trades in DB
    trade = MagicMock()
    trade.id = "trade-1"
    trade.symbol = "BTC/USDT"

    invalid_trade = MagicMock()
    invalid_trade.id = "trade-0"
    invalid_trade.symbol = None
    
    open_trades = [invalid_trade, trade]
    
    # Mock exchange open orders
    mock_adapter.fetch_open_orders.return_value = [{"id": "ord-1"}]
    
    executor.reconcile_state(open_trades)
    
    # Verify events
    # reconcile.symbol should be emitted
    mock_repo.append_event.assert_any_call(
        event_type="reconcile.symbol",
        level="INFO",
        payload={
            "symbol": "BTC/USDT",
            "db_open_trade": "trade-1",
            "exchange_open_orders": 1
        },
        public_safe=False
    )
    
    # reconcile.completed should be emitted
    mock_repo.append_event.assert_any_call(
        event_type="reconcile.completed",
        level="INFO",
        payload={"checked_trades": 2},
        public_safe=True
    )


def test_check_exits_stop_loss(executor, mock_repo, mock_adapter):
    """Execute stop loss exit when price crosses threshold."""
    trade_id = "trade-1"
    mock_repo.get_trade.return_value = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_price": 49000.0,
        "take_profit_price": 52000.0,
    }

    mock_adapter.create_order.return_value = {
        "id": "exit-1",
        "price": 48950.0,
        "average": 48940.0,
    }

    result = executor.check_exits(trade_id, current_price=48900.0)

    assert result is not None
    assert result["exit_reason"] == "STOP_LOSS"
    assert result["exit_order"]["exchange_order_id"] == "exit-1"
    assert result["trade"]["status"] == "CLOSED"


def test_check_exits_handles_error(executor, mock_repo, mock_adapter):
    """Emit error event when exit execution fails."""
    trade_id = "trade-2"
    mock_repo.get_trade.return_value = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_price": 49000.0,
        "take_profit_price": 52000.0,
    }

    mock_adapter.create_order.side_effect = Exception("Exit failed")

    result = executor.check_exits(trade_id, current_price=48900.0)

    assert result is None
    mock_repo.append_event.assert_called_with(
        event_type="error.exit_execution",
        level="ERROR",
        payload={
            "error": "Exit failed",
            "trade_id": trade_id,
            "reason": "STOP_LOSS",
        },
        public_safe=False
    )


def test_check_exits_returns_none_when_no_trigger(executor, mock_repo, mock_adapter):
    """Return None when price does not hit SL/TP."""
    trade_id = "trade-3"
    mock_repo.get_trade.return_value = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_price": 49000.0,
        "take_profit_price": 52000.0,
    }

    result = executor.check_exits(trade_id, current_price=50050.0)
    assert result is None
    mock_adapter.create_order.assert_not_called()


def test_check_exits_skips_non_open_trade(executor, mock_repo, mock_adapter):
    """Return None when trade is not open."""
    trade_id = "trade-4"
    mock_repo.get_trade.return_value = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "status": "CLOSED",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_price": 49000.0,
        "take_profit_price": 52000.0,
    }

    result = executor.check_exits(trade_id, current_price=48000.0)
    assert result is None
    mock_adapter.create_order.assert_not_called()


def test_check_exits_take_profit(executor, mock_repo, mock_adapter):
    """Execute take profit when price crosses threshold."""
    trade_id = "trade-5"
    mock_repo.get_trade.return_value = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "status": "OPEN",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_price": 49000.0,
        "take_profit_price": 52000.0,
    }

    mock_adapter.create_order.return_value = {"id": "exit-2", "price": 52050.0}

    result = executor.check_exits(trade_id, current_price=52100.0)

    assert result is not None
    assert result["exit_reason"] == "TAKE_PROFIT"


def test_check_exits_returns_none_when_trade_missing(executor, mock_repo, mock_adapter):
    """Return None when trade is missing."""
    mock_repo.get_trade.return_value = None
    result = executor.check_exits("missing", current_price=48000.0)
    assert result is None
    mock_adapter.create_order.assert_not_called()


def test_reconcile_state_error_logs(executor, mock_repo, mock_adapter):
    """Log reconcile errors when adapter connectivity fails."""
    mock_adapter.fetch_balance.side_effect = Exception("Connection failed")
    executor.reconcile_state([])

    mock_repo.append_event.assert_any_call(
        event_type="error.reconcile",
        level="ERROR",
        payload={"error": "Connection failed"},
        public_safe=False
    )
