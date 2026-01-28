"""Abstract execution engine interface."""

from abc import ABC, abstractmethod
from typing import Any

from quantsail_engine.models.trade_plan import TradePlan


class ExecutionEngine(ABC):
    """Abstract interface for trade execution."""

    @abstractmethod
    def execute_entry(self, plan: TradePlan) -> dict[str, Any] | None:
        """
        Execute entry for a trade plan.

        Args:
            plan: Trade plan to execute

        Returns:
            Dictionary with trade and orders data or None if failed
        """
        ...

    @abstractmethod
    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """
        Check if any exit conditions are met for an open trade.

        Args:
            trade_id: ID of the open trade
            current_price: Current market price

        Returns:
            Dictionary with exit data if exit triggered, None otherwise
        """
        ...

    def reconcile_state(self, open_trades: list[Any]) -> None:
        """
        Reconcile internal state with external exchange state on startup.
        
        Args:
            open_trades: List of open trade objects from DB
        """
        pass