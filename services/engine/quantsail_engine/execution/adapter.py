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
