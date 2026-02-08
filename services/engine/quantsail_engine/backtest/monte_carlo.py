"""Monte Carlo Stress Testing Framework.

This module implements 3 types of Monte Carlo simulations for robustness testing:
1. Trade Shuffle: Validates edge persists regardless of trade order
2. Parameter Jitter: Tests sensitivity to parameter variations
3. Cost Jitter: Stress tests against fee/slippage variations

Monte Carlo prevents curve-fitting by testing strategy robustness under randomized conditions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
import random
import copy

from quantsail_engine.backtest.metrics import BacktestMetrics


@dataclass
class MonteCarloRun:
    """Results from a single Monte Carlo run."""

    run_id: int
    test_type: str
    perturbation: dict[str, Any]
    metrics: BacktestMetrics


@dataclass
class MonteCarloResult:
    """Aggregate results from Monte Carlo simulations."""

    test_type: str
    runs: list[MonteCarloRun] = field(default_factory=list)
    num_simulations: int = 0

    # Statistics
    mean_profit_factor: float = 0.0
    std_profit_factor: float = 0.0
    percentile_5_profit_factor: float = 0.0
    percentile_95_profit_factor: float = 0.0

    mean_return_pct: float = 0.0
    std_return_pct: float = 0.0
    percentile_5_return_pct: float = 0.0
    percentile_95_return_pct: float = 0.0

    mean_max_drawdown_pct: float = 0.0
    percentile_95_max_drawdown_pct: float = 0.0

    # Pass/Fail
    passed: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_type": self.test_type,
            "num_simulations": self.num_simulations,
            "mean_profit_factor": self.mean_profit_factor,
            "std_profit_factor": self.std_profit_factor,
            "percentile_5_profit_factor": self.percentile_5_profit_factor,
            "percentile_95_profit_factor": self.percentile_95_profit_factor,
            "mean_return_pct": self.mean_return_pct,
            "std_return_pct": self.std_return_pct,
            "percentile_5_return_pct": self.percentile_5_return_pct,
            "percentile_95_return_pct": self.percentile_95_return_pct,
            "mean_max_drawdown_pct": self.mean_max_drawdown_pct,
            "percentile_95_max_drawdown_pct": self.percentile_95_max_drawdown_pct,
            "passed": self.passed,
            "rejection_reasons": self.rejection_reasons,
        }


# Type aliases
BacktestFn = Callable[[list[Any], dict[str, Any]], BacktestMetrics]
TradeShuffleFn = Callable[[list[dict[str, Any]]], BacktestMetrics]
TestType = Literal["trade_shuffle", "param_jitter", "cost_jitter"]


class MonteCarloSimulator:
    """Monte Carlo stress testing framework for strategy robustness validation.

    From IMPL_GUIDE §3 - Three types of stress tests:

    1. Trade Shuffle: Randomize trade order 1000x
       - If profit factor drops below 1.0 in >5% of runs → strategy is fragile

    2. Parameter Jitter: Add ±10% noise to optimized parameters 500x
       - If profit factor drops >25% → overfitted to exact params

    3. Cost Jitter: Randomize fees ±20%, slippage ±50% for 500x
       - If too many runs go negative → edge is too thin

    Example:
        >>> simulator = MonteCarloSimulator()
        >>> result = simulator.run_trade_shuffle(
        ...     trades=backtest_trades,
        ...     calculate_metrics=calc_fn,
        ...     num_simulations=1000
        ... )
        >>> print(f"5th percentile PF: {result.percentile_5_profit_factor:.2f}")
    """

    # Acceptance criteria (from IMPL_GUIDE §3)
    TRADE_SHUFFLE_MIN_5TH_PERCENTILE_PF = 1.0
    TRADE_SHUFFLE_MAX_FAILURE_RATE = 0.05  # 5%

    PARAM_JITTER_MAX_PF_DROP_PCT = 25.0
    PARAM_JITTER_NOISE_PCT = 10.0

    COST_JITTER_FEE_VARIATION_PCT = 20.0
    COST_JITTER_SLIPPAGE_VARIATION_PCT = 50.0
    COST_JITTER_MAX_NEGATIVE_RATE = 0.10  # 10%

    def __init__(self, seed: int | None = None):
        """Initialize Monte Carlo simulator.

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def run_trade_shuffle(
        self,
        trades: list[dict[str, Any]],
        calculate_metrics: TradeShuffleFn,
        num_simulations: int = 1000,
    ) -> MonteCarloResult:
        """Run trade shuffle Monte Carlo.

        Randomizes the order of trades to verify that edge is not
        dependent on specific sequence of wins/losses.

        Args:
            trades: List of trade dictionaries from backtest
            calculate_metrics: Function to calculate metrics from trade list
            num_simulations: Number of random shuffles

        Returns:
            MonteCarloResult with statistics and pass/fail
        """
        result = MonteCarloResult(
            test_type="trade_shuffle",
            num_simulations=num_simulations,
        )

        if not trades:
            result.rejection_reasons.append("No trades to shuffle")
            return result

        runs: list[MonteCarloRun] = []
        profit_factors: list[float] = []
        returns: list[float] = []
        drawdowns: list[float] = []
        failures = 0

        for i in range(num_simulations):
            # Shuffle trades
            shuffled = trades.copy()
            random.shuffle(shuffled)

            # Calculate metrics
            metrics = calculate_metrics(shuffled)

            run = MonteCarloRun(
                run_id=i,
                test_type="trade_shuffle",
                perturbation={"seed": i},
                metrics=metrics,
            )
            runs.append(run)

            pf = metrics.profit_factor if metrics.profit_factor < float("inf") else 10.0
            profit_factors.append(pf)
            returns.append(metrics.total_return_pct)
            drawdowns.append(metrics.max_drawdown_pct)

            if pf < 1.0:
                failures += 1

        result.runs = runs
        result = self._calculate_statistics(result, profit_factors, returns, drawdowns)

        # Check acceptance criteria
        failure_rate = failures / num_simulations
        result.passed = True
        rejections = []

        if result.percentile_5_profit_factor < self.TRADE_SHUFFLE_MIN_5TH_PERCENTILE_PF:
            rejections.append(
                f"5th percentile PF {result.percentile_5_profit_factor:.2f} < {self.TRADE_SHUFFLE_MIN_5TH_PERCENTILE_PF}"
            )
            result.passed = False

        if failure_rate > self.TRADE_SHUFFLE_MAX_FAILURE_RATE:
            rejections.append(
                f"Failure rate {failure_rate*100:.1f}% > {self.TRADE_SHUFFLE_MAX_FAILURE_RATE*100:.0f}%"
            )
            result.passed = False

        result.rejection_reasons = rejections
        return result

    def run_param_jitter(
        self,
        data: list[Any],
        backtest_fn: BacktestFn,
        base_params: dict[str, Any],
        jitter_params: list[str],
        num_simulations: int = 500,
        noise_pct: float | None = None,
    ) -> MonteCarloResult:
        """Run parameter jitter Monte Carlo.

        Adds ±noise% to specified parameters to test sensitivity.

        Args:
            data: Historical candle data
            backtest_fn: Function that runs backtest with (data, params) -> BacktestMetrics
            base_params: Optimized parameters to jitter
            jitter_params: List of parameter names to jitter
            num_simulations: Number of simulations
            noise_pct: Noise percentage (default: 10%)

        Returns:
            MonteCarloResult with statistics and pass/fail
        """
        noise = noise_pct or self.PARAM_JITTER_NOISE_PCT
        result = MonteCarloResult(
            test_type="param_jitter",
            num_simulations=num_simulations,
        )

        # First, get baseline metrics
        try:
            baseline_metrics = backtest_fn(data, base_params)
            baseline_pf = baseline_metrics.profit_factor
        except Exception as e:
            result.rejection_reasons.append(f"Baseline backtest failed: {e}")
            return result

        runs: list[MonteCarloRun] = []
        profit_factors: list[float] = []
        returns: list[float] = []
        drawdowns: list[float] = []

        for i in range(num_simulations):
            # Jitter parameters
            jittered = copy.deepcopy(base_params)
            perturbation = {}

            for param in jitter_params:
                if param in jittered and isinstance(jittered[param], (int, float)):
                    original = jittered[param]
                    # Add ±noise%
                    jitter_factor = 1 + random.uniform(-noise/100, noise/100)
                    jittered[param] = original * jitter_factor
                    perturbation[param] = jittered[param]

            try:
                metrics = backtest_fn(data, jittered)
            except Exception:
                # Skip invalid combinations
                continue

            run = MonteCarloRun(
                run_id=i,
                test_type="param_jitter",
                perturbation=perturbation,
                metrics=metrics,
            )
            runs.append(run)

            pf = metrics.profit_factor if metrics.profit_factor < float("inf") else 10.0
            profit_factors.append(pf)
            returns.append(metrics.total_return_pct)
            drawdowns.append(metrics.max_drawdown_pct)

        if not runs:
            result.rejection_reasons.append("All jittered backtests failed")
            return result

        result.runs = runs
        result = self._calculate_statistics(result, profit_factors, returns, drawdowns)

        # Check acceptance criteria
        result.passed = True
        rejections = []

        if baseline_pf > 0:
            pf_drop_pct = ((baseline_pf - result.mean_profit_factor) / baseline_pf) * 100
            if pf_drop_pct > self.PARAM_JITTER_MAX_PF_DROP_PCT:
                rejections.append(
                    f"PF dropped {pf_drop_pct:.1f}% (from {baseline_pf:.2f} to {result.mean_profit_factor:.2f}) > {self.PARAM_JITTER_MAX_PF_DROP_PCT}%"
                )
                result.passed = False

        result.rejection_reasons = rejections
        return result

    def run_cost_jitter(
        self,
        data: list[Any],
        backtest_fn: BacktestFn,
        base_params: dict[str, Any],
        base_fee_pct: float,
        base_slippage_pct: float,
        num_simulations: int = 500,
    ) -> MonteCarloResult:
        """Run cost jitter Monte Carlo.

        Randomizes fees (±20%) and slippage (±50%) to stress test edge stability.

        Args:
            data: Historical candle data
            backtest_fn: Function that runs backtest with (data, params) -> BacktestMetrics
                        params should include 'fee_pct' and 'slippage_pct'
            base_params: Base parameters
            base_fee_pct: Base fee percentage
            base_slippage_pct: Base slippage percentage
            num_simulations: Number of simulations

        Returns:
            MonteCarloResult with statistics and pass/fail
        """
        result = MonteCarloResult(
            test_type="cost_jitter",
            num_simulations=num_simulations,
        )

        runs: list[MonteCarloRun] = []
        profit_factors: list[float] = []
        returns: list[float] = []
        drawdowns: list[float] = []
        negatives = 0

        for i in range(num_simulations):
            # Jitter costs
            jittered = copy.deepcopy(base_params)

            fee_jitter = 1 + random.uniform(
                -self.COST_JITTER_FEE_VARIATION_PCT/100,
                self.COST_JITTER_FEE_VARIATION_PCT/100
            )
            slippage_jitter = 1 + random.uniform(
                -self.COST_JITTER_SLIPPAGE_VARIATION_PCT/100,
                self.COST_JITTER_SLIPPAGE_VARIATION_PCT/100
            )

            jittered["fee_pct"] = base_fee_pct * fee_jitter
            jittered["slippage_pct"] = base_slippage_pct * slippage_jitter

            perturbation = {
                "fee_pct": jittered["fee_pct"],
                "slippage_pct": jittered["slippage_pct"],
            }

            try:
                metrics = backtest_fn(data, jittered)
            except Exception:
                continue

            run = MonteCarloRun(
                run_id=i,
                test_type="cost_jitter",
                perturbation=perturbation,
                metrics=metrics,
            )
            runs.append(run)

            pf = metrics.profit_factor if metrics.profit_factor < float("inf") else 10.0
            profit_factors.append(pf)
            returns.append(metrics.total_return_pct)
            drawdowns.append(metrics.max_drawdown_pct)

            if metrics.net_profit_usd < 0:
                negatives += 1

        if not runs:
            result.rejection_reasons.append("All cost-jittered backtests failed")
            return result

        result.runs = runs
        result = self._calculate_statistics(result, profit_factors, returns, drawdowns)

        # Check acceptance criteria
        negative_rate = negatives / len(runs)
        result.passed = True
        rejections = []

        if negative_rate > self.COST_JITTER_MAX_NEGATIVE_RATE:
            rejections.append(
                f"Negative rate {negative_rate*100:.1f}% > {self.COST_JITTER_MAX_NEGATIVE_RATE*100:.0f}%"
            )
            result.passed = False

        result.rejection_reasons = rejections
        return result

    def _calculate_statistics(
        self,
        result: MonteCarloResult,
        profit_factors: list[float],
        returns: list[float],
        drawdowns: list[float],
    ) -> MonteCarloResult:
        """Calculate statistics across all runs."""
        if not profit_factors:
            return result

        # Sort for percentile calculation
        pf_sorted = sorted(profit_factors)
        ret_sorted = sorted(returns)
        dd_sorted = sorted(drawdowns)

        n = len(profit_factors)

        # Mean and std
        result.mean_profit_factor = sum(profit_factors) / n
        result.mean_return_pct = sum(returns) / n
        result.mean_max_drawdown_pct = sum(drawdowns) / n

        if n > 1:
            variance = sum((x - result.mean_profit_factor) ** 2 for x in profit_factors) / (n - 1)
            result.std_profit_factor = variance ** 0.5

            variance = sum((x - result.mean_return_pct) ** 2 for x in returns) / (n - 1)
            result.std_return_pct = variance ** 0.5

        # Percentiles (5th and 95th)
        idx_5 = int(n * 0.05)
        idx_95 = int(n * 0.95)

        result.percentile_5_profit_factor = pf_sorted[idx_5] if idx_5 < n else pf_sorted[-1]
        result.percentile_95_profit_factor = pf_sorted[idx_95] if idx_95 < n else pf_sorted[-1]
        result.percentile_5_return_pct = ret_sorted[idx_5] if idx_5 < n else ret_sorted[-1]
        result.percentile_95_return_pct = ret_sorted[idx_95] if idx_95 < n else ret_sorted[-1]
        result.percentile_95_max_drawdown_pct = dd_sorted[idx_95] if idx_95 < n else dd_sorted[-1]

        return result

    def run_all(
        self,
        trades: list[dict[str, Any]],
        data: list[Any],
        backtest_fn: BacktestFn,
        calc_metrics_fn: TradeShuffleFn,
        base_params: dict[str, Any],
        jitter_params: list[str],
        base_fee_pct: float = 0.1,
        base_slippage_pct: float = 0.05,
    ) -> dict[str, MonteCarloResult]:
        """Run all three Monte Carlo tests.

        Args:
            trades: Trades from baseline backtest
            data: Historical data
            backtest_fn: Backtest function
            calc_metrics_fn: Function to calculate metrics from trade list
            base_params: Optimized parameters
            jitter_params: Parameters to jitter
            base_fee_pct: Base fee percentage
            base_slippage_pct: Base slippage percentage

        Returns:
            Dict with results for each test type
        """
        results = {}

        results["trade_shuffle"] = self.run_trade_shuffle(
            trades=trades,
            calculate_metrics=calc_metrics_fn,
            num_simulations=1000,
        )

        results["param_jitter"] = self.run_param_jitter(
            data=data,
            backtest_fn=backtest_fn,
            base_params=base_params,
            jitter_params=jitter_params,
            num_simulations=500,
        )

        results["cost_jitter"] = self.run_cost_jitter(
            data=data,
            backtest_fn=backtest_fn,
            base_params=base_params,
            base_fee_pct=base_fee_pct,
            base_slippage_pct=base_slippage_pct,
            num_simulations=500,
        )

        return results
