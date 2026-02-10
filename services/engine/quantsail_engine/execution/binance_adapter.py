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

    def create_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_price: float,
        stop_limit_price: float,
        client_order_id_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Place a Binance OCO order (linked SL + TP).

        Tries native OCO first. If that fails, falls back to placing separate
        LIMIT (TP) + STOP_LOSS_LIMIT (SL) orders.

        Args:
            symbol: Trading pair (e.g. "BTC/USDT").
            side: Order side (e.g. "sell" for closing longs).
            quantity: Order quantity.
            take_profit_price: Limit price for the take-profit leg.
            stop_price: Stop trigger price for the stop-loss leg.
            stop_limit_price: Limit price after stop triggers.
            client_order_id_prefix: Prefix for client order IDs.

        Returns:
            Dict with 'tp_order_id', 'sl_order_id', and 'oco_mode' keys.
        """
        import logging
        logger = logging.getLogger(__name__)

        prefix = client_order_id_prefix or "QS"
        tp_client_id = f"{prefix}-TP"
        sl_client_id = f"{prefix}-SL"

        # Attempt native OCO via Binance-specific params
        try:
            result = self.client.create_order(
                symbol=symbol,
                type="limit",
                side=side.lower(),
                amount=quantity,
                price=take_profit_price,
                params={
                    "stopPrice": stop_price,
                    "stopLimitPrice": stop_limit_price,
                    "stopLimitTimeInForce": "GTC",
                    "newClientOrderId": tp_client_id,
                    "listClientOrderId": f"{prefix}-OCO",
                    "type": "oco",
                },
            )
            # Extract order IDs from OCO response
            tp_order_id = result.get("id", "")
            sl_order_id = ""
            # Parse Binance OCO response to find SL leg
            orders = result.get("orders", [])
            for order in orders:
                order_type = order.get("type", "").upper()
                if order_type in ("STOP_LOSS_LIMIT", "STOP_LOSS"):
                    sl_order_id = order.get("id", "")
                elif order_type == "LIMIT_MAKER":
                    tp_order_id = order.get("id", tp_order_id)

            if not sl_order_id:
                sl_order_id = result.get("info", {}).get("orderListId", "")

            logger.info(
                "OCO order placed: TP=%s, SL=%s, symbol=%s",
                tp_order_id, sl_order_id, symbol,
            )
            return {
                "tp_order_id": tp_order_id,
                "sl_order_id": sl_order_id,
                "oco_mode": "native",
                "raw": result,
            }
        except Exception as oco_err:
            logger.warning(
                "Native OCO failed for %s (%s). Falling back to separate orders.",
                symbol, oco_err,
            )

        # Fallback: place separate LIMIT (TP) + STOP_LOSS_LIMIT (SL)
        tp_result = self.client.create_order(
            symbol=symbol,
            type="limit",
            side=side.lower(),
            amount=quantity,
            price=take_profit_price,
            params={"newClientOrderId": tp_client_id, "timeInForce": "GTC"},
        )
        sl_result = self.client.create_order(
            symbol=symbol,
            type="stop_loss_limit" if "stop_loss_limit" in (
                self.client.options.get("orderTypes", {})
            ) else "STOP_LOSS_LIMIT",
            side=side.lower(),
            amount=quantity,
            price=stop_limit_price,
            params={
                "stopPrice": stop_price,
                "newClientOrderId": sl_client_id,
                "timeInForce": "GTC",
            },
        )

        logger.info(
            "Fallback separate orders placed: TP=%s, SL=%s, symbol=%s",
            tp_result.get("id"), sl_result.get("id"), symbol,
        )
        return {
            "tp_order_id": tp_result.get("id", ""),
            "sl_order_id": sl_result.get("id", ""),
            "oco_mode": "fallback",
            "tp_raw": tp_result,
            "sl_raw": sl_result,
        }

