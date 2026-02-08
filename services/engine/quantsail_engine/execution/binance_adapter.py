"""Binance Spot Adapter using CCXT."""

from typing import Any

try:
    import ccxt.pro as ccxt  # Use pro for websocket potential later, but base is fine
except ImportError:
    ccxt = None  # type: ignore[assignment]

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

        Raises:
            ImportError: If ccxt is not installed.
        """
        if ccxt is None:
            raise ImportError(
                "ccxt is required for live trading. Install with: pip install ccxt"
            )
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

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Fetch current ticker (last price, bid, ask).

        Args:
            symbol: CCXT symbol (e.g., "BTC/USDT")

        Returns:
            Ticker dict with 'last', 'bid', 'ask' keys
        """
        return self.client.fetch_ticker(symbol)

    def fetch_order_status(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Fetch order status by ID.

        Args:
            symbol: CCXT symbol (e.g., "BTC/USDT")
            order_id: Exchange order ID

        Returns:
            Order dict with 'status', 'filled', 'average', etc.
        """
        return self.client.fetch_order(order_id, symbol)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[list[Any]]:
        """Fetch OHLCV candles.

        Args:
            symbol: CCXT symbol (e.g., "BTC/USDT")
            timeframe: Candle timeframe (1m, 5m, 1h, 1d, etc.)
            limit: Number of candles to fetch

        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        return self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
