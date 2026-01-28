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
        "amount": 0.01,
        "datetime": "2024-01-01T12:00:00Z"
    }

    trade_id = executor.execute_entry(plan)

    assert trade_id == "uuid-123"
    
    # Verify idempotency key was used
    mock_adapter.create_order.assert_called_once()
    call_args = mock_adapter.create_order.call_args
    assert call_args.kwargs["client_order_id"] == "QS-uuid-123-ENTRY"
    
    # Verify persistence
    mock_repo.save_trade.assert_called_once()
    saved_trade = mock_repo.save_trade.call_args[0][0]
    assert saved_trade["id"] == "uuid-123"
    assert saved_trade["exchange_order_id"] == "exchange-order-999"
    assert saved_trade["entry_price"] == 50005.0  # From fill


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

    trade_id = executor.execute_entry(plan)

    assert trade_id == "uuid-123"
    
    # Verify exchange was NOT called
    mock_adapter.create_order.assert_not_called()
    mock_repo.save_trade.assert_not_called()


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
    
    open_trades = [trade]
    
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
        payload={"checked_trades": 1},
        public_safe=True
    )
