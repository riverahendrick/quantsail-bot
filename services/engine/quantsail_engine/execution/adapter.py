"""Abstract interface for exchange adapters."""

from typing import Protocol, Any


class ExchangeAdapter(Protocol):
    """Protocol for exchange interactions."""

    def fetch_balance(self) -> dict[str, float]:
        """Fetch current free balances."""
        ...

    def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Fetch open orders for a symbol."""
        ...

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new order."""
        ...

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Cancel an order."""
        ...

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Fetch current ticker (last, bid, ask)."""
        ...

    def fetch_order_status(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Fetch order status by exchange order ID."""
        ...

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
        """Place an OCO (One-Cancels-Other) order for linked SL + TP.

        If the exchange does not support native OCO, implementations should
        fall back to two separate orders and return metadata indicating that.

        Args:
            symbol: Trading pair.
            side: 'sell' for exit longs.
            quantity: Order quantity.
            take_profit_price: Limit price for the take-profit leg.
            stop_price: Stop trigger price for the stop-loss leg.
            stop_limit_price: Limit price for the stop-loss leg after trigger.
            client_order_id_prefix: Optional prefix for client order IDs.

        Returns:
            Dict with at minimum 'tp_order_id' and 'sl_order_id' keys.
        """
        ...
