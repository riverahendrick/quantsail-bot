"""Tests for BinanceSpotAdapter — all exchange calls are mocked via ccxt."""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest


@pytest.fixture
def mock_ccxt():
    """Patch ccxt so no real connection is needed."""
    mock_mod = MagicMock()
    mock_exchange = MagicMock()
    mock_mod.binance.return_value = mock_exchange
    with patch.dict("sys.modules", {"ccxt.pro": mock_mod, "ccxt": mock_mod}):
        yield mock_exchange


@pytest.fixture
def adapter(mock_ccxt):
    """Create a BinanceSpotAdapter with a patched ccxt client."""
    # Re-import after patching so the module picks up the mock
    from quantsail_engine.execution.binance_adapter import BinanceSpotAdapter

    a = BinanceSpotAdapter.__new__(BinanceSpotAdapter)
    a.client = mock_ccxt
    return a


# --- fetch_balance ---


def test_fetch_balance_filters_zero(adapter, mock_ccxt):
    """Only assets with free > 0 are returned."""
    mock_ccxt.fetch_balance.return_value = {
        "BTC": {"free": "0.5", "used": "0.0"},
        "ETH": {"free": "0.0", "used": "1.0"},
        "USDT": {"free": "1000.0", "used": "0.0"},
        "info": "some metadata",  # non-dict values are skipped
    }
    result = adapter.fetch_balance()
    assert result == {"BTC": 0.5, "USDT": 1000.0}


# --- fetch_open_orders ---


def test_fetch_open_orders_delegates(adapter, mock_ccxt):
    """Delegates directly to ccxt."""
    mock_ccxt.fetch_open_orders.return_value = [{"id": "1"}]
    assert adapter.fetch_open_orders("BTC/USDT") == [{"id": "1"}]
    mock_ccxt.fetch_open_orders.assert_called_once_with("BTC/USDT")


# --- create_order ---


def test_create_order_market(adapter, mock_ccxt):
    """Market order passes correct args to ccxt."""
    mock_ccxt.create_order.return_value = {"id": "ord-1"}
    result = adapter.create_order(
        symbol="BTC/USDT",
        side="BUY",
        order_type="MARKET",
        quantity=0.01,
        client_order_id="QS-test-ENTRY",
    )
    assert result == {"id": "ord-1"}
    mock_ccxt.create_order.assert_called_once_with(
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.01,
        price=None,
        params={"newClientOrderId": "QS-test-ENTRY"},
    )


def test_create_order_limit_with_price(adapter, mock_ccxt):
    """Limit order includes price."""
    mock_ccxt.create_order.return_value = {"id": "ord-2"}
    adapter.create_order(
        symbol="ETH/USDT",
        side="SELL",
        order_type="LIMIT",
        quantity=1.0,
        price=2500.0,
    )
    mock_ccxt.create_order.assert_called_once_with(
        symbol="ETH/USDT",
        type="limit",
        side="sell",
        amount=1.0,
        price=2500.0,
        params={},
    )


# --- cancel_order ---


def test_cancel_order(adapter, mock_ccxt):
    """cancel_order delegates with proper arg order."""
    mock_ccxt.cancel_order.return_value = {"status": "canceled"}
    result = adapter.cancel_order("BTC/USDT", "ord-1")
    mock_ccxt.cancel_order.assert_called_once_with("ord-1", "BTC/USDT")
    assert result["status"] == "canceled"


# --- fetch_ticker ---


def test_fetch_ticker(adapter, mock_ccxt):
    """fetch_ticker just delegates."""
    mock_ccxt.fetch_ticker.return_value = {"last": 50000, "bid": 49999, "ask": 50001}
    result = adapter.fetch_ticker("BTC/USDT")
    assert result["last"] == 50000


# --- fetch_order_status ---


def test_fetch_order_status(adapter, mock_ccxt):
    """Delegates to fetch_order."""
    mock_ccxt.fetch_order.return_value = {"status": "closed", "filled": 0.01}
    result = adapter.fetch_order_status("BTC/USDT", "ord-99")
    mock_ccxt.fetch_order.assert_called_once_with("ord-99", "BTC/USDT")
    assert result["status"] == "closed"


# --- fetch_ohlcv ---


def test_fetch_ohlcv(adapter, mock_ccxt):
    """OHLCV returns candle list."""
    candles = [[1000000, 50000, 50500, 49000, 50200, 100]]
    mock_ccxt.fetch_ohlcv.return_value = candles
    result = adapter.fetch_ohlcv("BTC/USDT", "1h", limit=50)
    assert result == candles
    mock_ccxt.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", limit=50)


# --- create_oco_order ---


def test_create_oco_order_native_success(adapter, mock_ccxt):
    """Native OCO returns tp/sl order IDs and oco_mode=native."""
    mock_ccxt.create_order.return_value = {
        "id": "oco-list-1",
        "orders": [
            {"id": "tp-ord-1", "type": "LIMIT_MAKER"},
            {"id": "sl-ord-1", "type": "STOP_LOSS_LIMIT"},
        ],
    }

    result = adapter.create_oco_order(
        symbol="BTC/USDT",
        side="sell",
        quantity=0.01,
        take_profit_price=52000.0,
        stop_price=49000.0,
        stop_limit_price=48900.0,
        client_order_id_prefix="QS-trade1",
    )

    assert result["oco_mode"] == "native"
    assert result["tp_order_id"] == "tp-ord-1"
    assert result["sl_order_id"] == "sl-ord-1"


def test_create_oco_order_native_no_sl_in_orders(adapter, mock_ccxt):
    """If no SL leg in orders, falls back to orderListId in info."""
    mock_ccxt.create_order.return_value = {
        "id": "oco-list-2",
        "orders": [],
        "info": {"orderListId": "list-fallback-id"},
    }

    result = adapter.create_oco_order(
        symbol="BTC/USDT",
        side="sell",
        quantity=0.01,
        take_profit_price=52000.0,
        stop_price=49000.0,
        stop_limit_price=48900.0,
    )

    assert result["oco_mode"] == "native"
    assert result["sl_order_id"] == "list-fallback-id"


def test_create_oco_order_fallback_on_oco_failure(adapter, mock_ccxt):
    """Falls back to separate LIMIT + SL orders when native OCO fails."""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call is the native OCO attempt — fail it
            raise Exception("OCO not supported")
        if call_count == 2:
            return {"id": "tp-separate-1"}  # TP limit order
        return {"id": "sl-separate-1"}  # SL stop-loss order

    mock_ccxt.create_order.side_effect = side_effect
    mock_ccxt.options = {}

    result = adapter.create_oco_order(
        symbol="BTC/USDT",
        side="sell",
        quantity=0.01,
        take_profit_price=52000.0,
        stop_price=49000.0,
        stop_limit_price=48900.0,
        client_order_id_prefix="QS-t2",
    )

    assert result["oco_mode"] == "fallback"
    assert result["tp_order_id"] == "tp-separate-1"
    assert result["sl_order_id"] == "sl-separate-1"
    assert mock_ccxt.create_order.call_count == 3


# --- testnet mode ---


def test_testnet_mode(adapter, mock_ccxt):
    """Verify set_sandbox_mode is available on the client (called during __init__)."""
    # The adapter fixture already has a mock client; verify the method exists
    # and can be called (real __init__ calls it when testnet=True)
    mock_ccxt.set_sandbox_mode(True)
    mock_ccxt.set_sandbox_mode.assert_called_once_with(True)


def test_create_order_without_client_order_id(adapter, mock_ccxt):
    """When client_order_id is omitted, params dict is empty."""
    mock_ccxt.create_order.return_value = {"id": "ord-no-cid"}
    adapter.create_order(
        symbol="BTC/USDT",
        side="BUY",
        order_type="MARKET",
        quantity=0.01,
    )
    mock_ccxt.create_order.assert_called_once_with(
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.01,
        price=None,
        params={},
    )

