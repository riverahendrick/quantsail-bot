"""Profitability gate implementation."""

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

    def evaluate(self, plan: TradePlan) -> tuple[bool, float]:
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
            Tuple of (passed, expected_net_profit_usd)
        """
        # Use TP target for expected profit calculation
        expected_gross_profit_usd = plan.reward_usd

        expected_net_profit_usd = (
            expected_gross_profit_usd
            - plan.estimated_fee_usd
            - plan.estimated_slippage_usd
            - plan.estimated_spread_cost_usd
        )

        passed = expected_net_profit_usd >= self.min_profit_usd

        return passed, expected_net_profit_usd
