"""Abstract execution engine interface."""

from abc import ABC, abstractmethod
from typing import Any

from quantsail_engine.models.trade_plan import TradePlan


class ExecutionEngine(ABC):
    """Abstract interface for trade execution."""

    @abstractmethod
    def execute_entry(self, plan: TradePlan) -> dict[str, Any]:
        """
        Execute entry for a trade plan.

        Args:
            plan: Trade plan to execute

        Returns:
            Dictionary with trade and orders data
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
