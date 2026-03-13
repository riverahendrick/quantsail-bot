"""Tests for LiveExecutor — extended coverage for protective order polling,
zero fill, partial fill, and OCO failure paths.

Supplements existing test_live_execution.py which covers entry success/failure,
idempotency, fallback exits, and reconciliation.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest

from quantsail_engine.execution.live_executor import LiveExecutor
from quantsail_engine.models.trade_plan import TradePlan


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_trade.return_value = None
    return repo


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.create_oco_order.return_value = {
        "tp_order_id": "tp-1",
        "sl_order_id": "sl-1",
        "oco_mode": "native",
    }
    return adapter


@pytest.fixture
def executor(mock_repo, mock_adapter):
    return LiveExecutor(mock_repo, mock_adapter)


def _make_plan(**overrides):
    defaults = {
        "symbol": "BTC/USDT",
        "side": "BUY",
        "entry_price": 50000.0,
        "quantity": 0.01,
        "stop_loss_price": 49000.0,
        "take_profit_price": 52000.0,
        "estimated_fee_usd": 1.0,
        "estimated_slippage_usd": 0.5,
        "estimated_spread_cost_usd": 0.5,
        "trade_id": "uuid-ext-1",
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return TradePlan(**defaults)


# --- Zero fill ---


def test_execute_entry_zero_fill_returns_none(executor, mock_repo, mock_adapter):
    """Returns None when exchange fills zero quantity."""
    plan = _make_plan(trade_id="zero-fill-1")
    mock_adapter.create_order.return_value = {
        "id": "ord-zero",
        "average": 50000.0,
        "filled": 0,
        "amount": 0,
    }

    result = executor.execute_entry(plan)

    assert result is None
    mock_repo.append_event.assert_any_call(
        event_type="error.zero_fill",
        level="ERROR",
        payload={"trade_id": "zero-fill-1", "response": str(mock_adapter.create_order.return_value)},
        public_safe=False,
    )


# --- Partial fill ---


def test_execute_entry_partial_fill_logs_warning(executor, mock_repo, mock_adapter):
    """Partial fill is accepted but a warning event is emitted."""
    plan = _make_plan(trade_id="partial-1", quantity=0.10)
    mock_adapter.create_order.return_value = {
        "id": "ord-partial",
        "average": 50000.0,
        "filled": 0.05,  # Only half filled
    }

    result = executor.execute_entry(plan)

    assert result is not None
    trade = result["trade"]
    assert trade["quantity"] == 0.05  # Uses filled qty, not requested
    mock_repo.append_event.assert_any_call(
        event_type="execution.partial_fill",
        level="WARN",
        payload={
            "trade_id": "partial-1",
            "requested_qty": 0.10,
            "filled_qty": 0.05,
        },
        public_safe=False,
    )


# --- OCO placement failure ---


def test_execute_entry_oco_failure_still_returns_trade(executor, mock_repo, mock_adapter):
    """Trade is returned even when OCO placement fails (position is unprotected)."""
    plan = _make_plan(trade_id="oco-fail-1")
    mock_adapter.create_order.return_value = {
        "id": "ord-ok",
        "average": 50000.0,
        "filled": 0.01,
    }
    mock_adapter.create_oco_order.side_effect = Exception("OCO failed")

    result = executor.execute_entry(plan)

    assert result is not None
    # Only entry order, no protective orders
    assert len(result["orders"]) == 1
    mock_repo.append_event.assert_any_call(
        event_type="error.protective_orders",
        level="ERROR",
        payload={"trade_id": "oco-fail-1", "symbol": "BTC/USDT"},
        public_safe=False,
    )


# --- Protective order polling: SL fill ---


def test_poll_protective_sl_fill(executor, mock_repo, mock_adapter):
    """When SL order is filled, trade is closed and TP is cancelled."""
    trade_id = "poll-sl-1"
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

    # Register protective orders
    executor._protective_orders[trade_id] = {
        "sl_order_id": "sl-ord-1",
        "tp_order_id": "tp-ord-1",
        "symbol": "BTC/USDT",
    }

    # SL is filled
    mock_adapter.fetch_order_status.side_effect = lambda sym, oid: (
        {"status": "closed", "average": 48950.0, "id": "sl-ord-1"}
        if oid == "sl-ord-1"
        else {"status": "open", "id": "tp-ord-1"}
    )

    result = executor.check_exits(trade_id, current_price=48900.0)

    assert result is not None
    assert result["exit_reason"] == "STOP_LOSS"
    assert result["trade"]["status"] == "CLOSED"
    # TP should be cancelled
    mock_adapter.cancel_order.assert_called_once_with("BTC/USDT", "tp-ord-1")
    # Protective orders cleaned up
    assert trade_id not in executor._protective_orders


# --- Protective order polling: TP fill ---


def test_poll_protective_tp_fill(executor, mock_repo, mock_adapter):
    """When TP order is filled, trade is closed and SL is cancelled."""
    trade_id = "poll-tp-1"
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

    executor._protective_orders[trade_id] = {
        "sl_order_id": "sl-ord-2",
        "tp_order_id": "tp-ord-2",
        "symbol": "BTC/USDT",
    }

    mock_adapter.fetch_order_status.side_effect = lambda sym, oid: (
        {"status": "open", "id": "sl-ord-2"}
        if oid == "sl-ord-2"
        else {"status": "closed", "average": 52100.0, "id": "tp-ord-2"}
    )

    result = executor.check_exits(trade_id, current_price=52200.0)

    assert result is not None
    assert result["exit_reason"] == "TAKE_PROFIT"
    assert result["trade"]["pnl_usd"] == pytest.approx((52100.0 - 50000.0) * 0.01, abs=0.01)
    mock_adapter.cancel_order.assert_called_once_with("BTC/USDT", "sl-ord-2")


# --- Protective order polling: cancel fails gracefully ---


def test_poll_cancel_other_leg_failure_graceful(executor, mock_repo, mock_adapter):
    """Cancel failure on other leg is logged but doesn't prevent exit."""
    trade_id = "cancel-fail-1"
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

    executor._protective_orders[trade_id] = {
        "sl_order_id": "sl-ord-3",
        "tp_order_id": "tp-ord-3",
        "symbol": "BTC/USDT",
    }

    mock_adapter.fetch_order_status.side_effect = lambda sym, oid: (
        {"status": "closed", "average": 48900.0, "id": "sl-ord-3"}
        if oid == "sl-ord-3"
        else {"status": "open"}
    )
    mock_adapter.cancel_order.side_effect = Exception("Already cancelled")

    result = executor.check_exits(trade_id, current_price=48900.0)

    # Exit still succeeds despite cancel failure
    assert result is not None
    assert result["exit_reason"] == "STOP_LOSS"


# --- Protective order polling: exchange error ---


def test_poll_protective_exchange_error(executor, mock_repo, mock_adapter):
    """Exchange error during polling emits warning, returns None."""
    trade_id = "poll-err-1"
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

    executor._protective_orders[trade_id] = {
        "sl_order_id": "sl-err",
        "tp_order_id": "tp-err",
        "symbol": "BTC/USDT",
    }

    mock_adapter.fetch_order_status.side_effect = Exception("Network timeout")

    result = executor.check_exits(trade_id, current_price=50000.0)

    assert result is None
    mock_repo.append_event.assert_any_call(
        event_type="error.poll_protective",
        level="WARN",
        payload={"trade_id": trade_id, "error": "Network timeout"},
        public_safe=False,
    )


# --- Extract fill price ---


def test_extract_fill_price_average():
    """Uses 'average' field when present."""
    assert LiveExecutor._extract_fill_price({"average": 50100.0}, 50000.0) == 50100.0


def test_extract_fill_price_fallback_to_price():
    """Falls back to 'price' when no 'average'."""
    assert LiveExecutor._extract_fill_price({"price": 50050.0}, 50000.0) == 50050.0


def test_extract_fill_price_fallback_default():
    """Falls back to provided default when nothing else available."""
    assert LiveExecutor._extract_fill_price({}, 50000.0) == 50000.0


# --- Make protective order record ---


def test_make_protective_order_record_sl():
    """Creates correct SL protective order record."""
    plan = _make_plan(trade_id="rec-1")
    now = datetime.now(timezone.utc)
    record = LiveExecutor._make_protective_order_record(plan, "STOP_LOSS", "sl-ex-1", now)

    assert record["order_type"] == "STOP_LOSS"
    assert record["price"] == plan.stop_loss_price
    assert record["client_order_id"] == "QS-rec-1-STOP_LOSS"
    assert record["status"] == "PENDING"


def test_make_protective_order_record_tp():
    """Creates correct TP protective order record."""
    plan = _make_plan(trade_id="rec-2")
    now = datetime.now(timezone.utc)
    record = LiveExecutor._make_protective_order_record(plan, "TAKE_PROFIT", "tp-ex-1", now)

    assert record["order_type"] == "TAKE_PROFIT"
    assert record["price"] == plan.take_profit_price
    assert record["client_order_id"] == "QS-rec-2-TAKE_PROFIT"


# --- Reconcile with matched protective orders ---


def test_reconcile_reindexes_existing_protective_orders(executor, mock_repo, mock_adapter):
    """Reconcile picks up existing SL/TP orders matching the trade prefix."""
    trade = MagicMock()
    trade.id = "recon-1"
    trade.symbol = "ETH/USDT"

    mock_adapter.fetch_open_orders.return_value = [
        {"id": "sl-recon", "clientOrderId": "QS-recon-1-SL"},
        {"id": "tp-recon", "clientOrderId": "QS-recon-1-TP"},
        {"id": "other-ord", "clientOrderId": "UNRELATED"},
    ]

    executor.reconcile_state([trade])

    assert "recon-1" in executor._protective_orders
    prot = executor._protective_orders["recon-1"]
    assert prot["sl_order_id"] == "sl-recon"
    assert prot["tp_order_id"] == "tp-recon"
    assert prot["oco_mode"] == "reconciled"
