"""Binance Spot Adapter using CCXT."""

from typing import Any
import ccxt.pro as ccxt  # Use pro for websocket potential later, but base is fine
from quantsail_engine.execution.adapter import ExchangeAdapter


class BinanceSpotAdapter(ExchangeAdapter):
    """Binance Spot adapter implementation."""

    def __init__(self, api_key: str, secret: str, testnet: bool = False):
        """
        Initialize Binance adapter.

        Args:
            api_key: Exchange API key
            secret: Exchange Secret
            testnet: Whether to use testnet
        """
        self.client = ccxt.binance({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        if testnet:
            self.client.set_sandbox_mode(True)

    def fetch_balance(self) -> dict[str, float]:
        """Fetch free balances."""
        balance = self.client.fetch_balance()
        return {
            asset: float(data["free"])
            for asset, data in balance.items()
            if isinstance(data, dict) and "free" in data and float(data["free"]) > 0
        }

    def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Fetch open orders."""
        return self.client.fetch_open_orders(symbol)

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new order.
        
        Note: CCXT standardizes params. clientOrderId is usually in params.
        """
        params = {}
        if client_order_id:
            params["newClientOrderId"] = client_order_id

        return self.client.create_order(
            symbol=symbol,
            type=order_type.lower(),
            side=side.lower(),
            amount=quantity,
            price=price,
            params=params,
        )

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Cancel an order."""
        return self.client.cancel_order(order_id, symbol)
