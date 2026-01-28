from __future__ import annotations

from typing import Any

import pytest

from quantsail_engine.execution import binance_adapter as adapter_module


class StubClient:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None
        self.sandbox_mode: bool | None = None

    def set_sandbox_mode(self, enabled: bool) -> None:
        self.sandbox_mode = enabled

    def fetch_balance(self) -> dict[str, Any]:
        return {
            "USDT": {"free": "10"},
            "BTC": {"free": "0"},
            "info": {},
        }

    def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return [{"id": "open-1", "symbol": symbol}]

    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.last_params = {
            "symbol": symbol,
            "type": type,
            "side": side,
            "amount": amount,
            "price": price,
            "params": params or {},
        }
        return {"id": "order-1"}

    def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        return {"id": order_id, "symbol": symbol}


class StubCcxt:
    def __init__(self) -> None:
        self.client = StubClient()

    def binance(self, _config: dict[str, Any]) -> StubClient:
        return self.client


def test_binance_adapter_fetch_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_ccxt = StubCcxt()
    monkeypatch.setattr(adapter_module, "ccxt", stub_ccxt)

    adapter = adapter_module.BinanceSpotAdapter("key", "secret", testnet=True)
    assert stub_ccxt.client.sandbox_mode is True

    balances = adapter.fetch_balance()
    assert balances == {"USDT": 10.0}


def test_binance_adapter_order_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_ccxt = StubCcxt()
    monkeypatch.setattr(adapter_module, "ccxt", stub_ccxt)

    adapter = adapter_module.BinanceSpotAdapter("key", "secret", testnet=False)
    open_orders = adapter.fetch_open_orders("BTC/USDT")
    assert open_orders[0]["id"] == "open-1"

    result = adapter.create_order(
        symbol="BTC/USDT",
        side="BUY",
        order_type="market",
        quantity=0.01,
        client_order_id="client-123",
    )
    assert result["id"] == "order-1"
    assert stub_ccxt.client.last_params is not None
    assert stub_ccxt.client.last_params["params"]["newClientOrderId"] == "client-123"

    cancel = adapter.cancel_order("BTC/USDT", "order-1")
    assert cancel["id"] == "order-1"
