"""Profitability gate implementation."""

from typing import Any

from quantsail_engine.models.trade_plan import TradePlan


class ProfitabilityGate:
    """Gate that rejects trades below minimum expected profit."""

    def __init__(self, min_profit_usd: float):
        """
        Initialize profitability gate.

        Args:
            min_profit_usd: Minimum expected net profit in USD to accept a trade
        """
        self.min_profit_usd = min_profit_usd

    def evaluate(self, plan: TradePlan) -> tuple[bool, dict[str, Any]]:
        """
        Evaluate if trade plan meets profitability requirements.

        Formula:
        expected_net_profit_usd =
            expected_gross_profit_usd
            - fee_est_usd
            - slippage_est_usd
            - spread_cost_est_usd

        Args:
            plan: Trade plan to evaluate

        Returns:
            Tuple of (passed, breakdown_dict)
        """
        # Gross profit: (TP - Entry) * Qty
        # Note: Entry here should be the "Average Fill Price" if we want accuracy,
        # but typically TradePlan.entry_price is the trigger price or mid.
        # Let's assume TradePlan.entry_price is the reference price (e.g. Mid or Best Ask).
        # Gross Profit is conventionally distance from Entry to TP.
        expected_gross_profit_usd = plan.reward_usd

        expected_net_profit_usd = (
            expected_gross_profit_usd
            - plan.estimated_fee_usd
            - plan.estimated_slippage_usd
            - plan.estimated_spread_cost_usd
        )

        passed = expected_net_profit_usd >= self.min_profit_usd

        breakdown = {
            "entry_price": plan.entry_price,
            "tp_price": plan.take_profit_price,
            "quantity": plan.quantity,
            "gross_profit_usd": expected_gross_profit_usd,
            "fee_usd": plan.estimated_fee_usd,
            "slippage_usd": plan.estimated_slippage_usd,
            "spread_cost_usd": plan.estimated_spread_cost_usd,
            "net_profit_usd": expected_net_profit_usd,
            "min_profit_usd": self.min_profit_usd,
            "passed": passed,
        }

        return passed, breakdown
