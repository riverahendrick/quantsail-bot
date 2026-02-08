"""Walk-Forward Analysis (WFA) Framework.

This module implements the gold standard for strategy validation:
- Rolling optimization windows
- Out-of-sample testing
- Parameter robustness verification

Walk-forward prevents overfitting by ensuring strategies are tested on truly unseen data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

import numpy as np
from quantsail_engine.backtest.metrics import BacktestMetrics, MetricsCalculator


@dataclass
class WFAWindow:
    """Results from a single walk-forward window."""

    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: dict[str, Any]
    train_metrics: BacktestMetrics
    test_metrics: BacktestMetrics


@dataclass
class WFAResult:
    """Aggregate results from walk-forward analysis."""

    windows: list[WFAWindow] = field(default_factory=list)
    aggregate_trades: int = 0
    aggregate_net_profit_usd: float = 0.0
    aggregate_profit_factor: float = 0.0
    aggregate_win_rate: float = 0.0
    avg_daily_pnl: float = 0.0
    worst_window_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    passed: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "windows": len(self.windows),
            "aggregate_trades": self.aggregate_trades,
            "aggregate_net_profit_usd": self.aggregate_net_profit_usd,
            "aggregate_profit_factor": self.aggregate_profit_factor,
            "aggregate_win_rate": self.aggregate_win_rate,
            "avg_daily_pnl": self.avg_daily_pnl,
            "worst_window_return_pct": self.worst_window_return_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "passed": self.passed,
            "rejection_reasons": self.rejection_reasons,
        }


# Type alias for backtest function
BacktestFn = Callable[[list[Any], dict[str, Any]], BacktestMetrics]


class WalkForwardAnalyzer:
    """Walk-Forward Analysis framework for strategy validation.

    Process (per symbol/timeframe/strategy):
        1. Split data into rolling train/test windows
        2. Optimize parameters on training window
        3. Test on out-of-sample window
        4. Aggregate all test period results

    Example:
        >>> analyzer = WalkForwardAnalyzer(train_days=90, test_days=30, step_days=30)
        >>> result = analyzer.run(
        ...     data=historical_candles,
        ...     backtest_fn=run_backtest,
        ...     param_grid={'ema_fast': [5, 10, 15], 'ema_slow': [20, 30, 50]}
        ... )
        >>> print(f"Passed: {result.passed}, Reason: {result.rejection_reasons}")
    """

    # Acceptance criteria thresholds (from IMPL_GUIDE §2.3)
    MIN_PROFIT_FACTOR = 1.1
    MAX_WORST_WINDOW_LOSS_PCT = -5.0
    MIN_AVG_DAILY_PNL = 1.50
    MAX_DRAWDOWN_PCT = 15.0
    MIN_AGGREGATE_TRADES = 50

    def __init__(
        self,
        train_days: int = 90,
        test_days: int = 30,
        step_days: int = 30,
    ):
        """Initialize walk-forward analyzer.

        Args:
            train_days: Number of days for each training window
            test_days: Number of days for each test window
            step_days: Number of days to step forward between windows
        """
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days

    def run(
        self,
        data: list[Any],
        backtest_fn: BacktestFn,
        param_grid: dict[str, list[Any]],
        starting_equity: float = 10000.0,
    ) -> WFAResult:
        """Run walk-forward analysis.

        Args:
            data: Historical candle data (must have 'timestamp' attribute/key)
            backtest_fn: Function that runs backtest with (data, params) -> BacktestMetrics
            param_grid: Parameters to optimize, e.g. {'ema_fast': [5, 10], 'ema_slow': [20, 30]}
            starting_equity: Starting equity for metrics calculation

        Returns:
            WFAResult with aggregate metrics and pass/fail status
        """
        if not data:
            raise ValueError("Data cannot be empty")

        windows: list[WFAWindow] = []
        all_test_metrics: list[BacktestMetrics] = []

        # Extract timestamps from data
        timestamps = self._extract_timestamps(data)
        data_start = min(timestamps)
        data_end = max(timestamps)

        # Calculate total span in days
        total_days = (data_end - data_start).days
        min_required = self.train_days + self.test_days

        if total_days < min_required:
            result = WFAResult()
            result.rejection_reasons.append(
                f"Insufficient data: {total_days} days, need {min_required}"
            )
            return result

        # Generate windows
        window_id = 0
        window_start = data_start

        while True:
            train_end = window_start + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)

            if test_end > data_end:
                break

            # Split data
            train_data = self._filter_by_time(data, timestamps, window_start, train_end)
            test_data = self._filter_by_time(data, timestamps, test_start, test_end)

            if not train_data or not test_data:
                window_start += timedelta(days=self.step_days)
                continue

            # Optimize on training data
            best_params, train_metrics = self._optimize_params(
                train_data, backtest_fn, param_grid
            )

            # Test on out-of-sample data
            test_metrics = backtest_fn(test_data, best_params)

            window = WFAWindow(
                window_id=window_id,
                train_start=window_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                best_params=best_params,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
            )

            windows.append(window)
            all_test_metrics.append(test_metrics)

            window_id += 1
            window_start += timedelta(days=self.step_days)

        # Aggregate results
        return self._aggregate_results(windows, all_test_metrics)

    def _extract_timestamps(self, data: list[Any]) -> list[datetime]:
        """Extract timestamps from candle data."""
        timestamps = []
        for item in data:
            if hasattr(item, "timestamp"):
                timestamps.append(item.timestamp)
            elif isinstance(item, dict) and "timestamp" in item:
                ts = item["timestamp"]
                if isinstance(ts, str):
                    timestamps.append(datetime.fromisoformat(ts))
                else:
                    timestamps.append(ts)
            elif isinstance(item, (list, tuple)) and len(item) > 0:
                # Assume first element is timestamp (OHLCV format)
                ts = item[0]
                if isinstance(ts, (int, float)):
                    # Milliseconds timestamp
                    timestamps.append(datetime.fromtimestamp(ts / 1000))
                else:
                    timestamps.append(ts)
        return timestamps

    def _filter_by_time(
        self,
        data: list[Any],
        timestamps: list[datetime],
        start: datetime,
        end: datetime,
    ) -> list[Any]:
        """Filter data by time range."""
        result = []
        for item, ts in zip(data, timestamps):
            if start <= ts < end:
                result.append(item)
        return result

    def _optimize_params(
        self,
        train_data: list[Any],
        backtest_fn: BacktestFn,
        param_grid: dict[str, list[Any]],
    ) -> tuple[dict[str, Any], BacktestMetrics]:
        """Find best parameters on training data.

        Uses simple grid search to find parameters that maximize profit factor.
        """
        param_combinations = self._generate_param_combinations(param_grid)

        best_params: dict[str, Any] = {}
        best_metrics: BacktestMetrics | None = None
        best_score = float("-inf")

        for params in param_combinations:
            try:
                metrics = backtest_fn(train_data, params)
                # Score by profit factor (or net profit if PF is 0)
                score = metrics.profit_factor if metrics.profit_factor > 0 else metrics.net_profit_usd
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_metrics = metrics
            except Exception:
                # Skip invalid parameter combinations
                continue

        if best_metrics is None:
            # Fallback to first combination if all failed
            if param_combinations:
                best_params = param_combinations[0]
                best_metrics = backtest_fn(train_data, best_params)
            else:
                raise ValueError("No valid parameter combinations found")

        return best_params, best_metrics

    def _generate_param_combinations(
        self, param_grid: dict[str, list[Any]]
    ) -> list[dict[str, Any]]:
        """Generate all combinations of parameters."""
        if not param_grid:
            return [{}]

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        combinations = []

        def recurse(idx: int, current: dict[str, Any]) -> None:
            if idx == len(keys):
                combinations.append(current.copy())
                return
            key = keys[idx]
            for val in values[idx]:
                current[key] = val
                recurse(idx + 1, current)

        recurse(0, {})
        return combinations

    def _aggregate_results(
        self,
        windows: list[WFAWindow],
        test_metrics: list[BacktestMetrics],
    ) -> WFAResult:
        """Aggregate results from all windows and check acceptance criteria."""
        result = WFAResult(windows=windows)

        if not windows:
            result.rejection_reasons.append("No valid walk-forward windows generated")
            return result

        # Calculate aggregates
        total_trades = sum(m.total_trades for m in test_metrics)
        total_winners = sum(m.winning_trades for m in test_metrics)
        total_net_profit = sum(m.net_profit_usd for m in test_metrics)
        
        # Calculate gross profit/loss from win/loss averages when direct fields not available
        total_gross_profit = sum(m.avg_win_usd * m.winning_trades for m in test_metrics)
        total_gross_loss = sum(m.avg_loss_usd * m.losing_trades for m in test_metrics)

        result.aggregate_trades = total_trades
        result.aggregate_net_profit_usd = total_net_profit
        result.aggregate_win_rate = (total_winners / total_trades * 100) if total_trades > 0 else 0.0

        # Profit factor
        if abs(total_gross_loss) > 0.01:
            result.aggregate_profit_factor = abs(total_gross_profit / total_gross_loss)
        else:
            result.aggregate_profit_factor = float("inf") if total_gross_profit > 0 else 0.0

        # Calculate days and avg daily PnL
        total_days = sum(
            (w.test_end - w.test_start).days for w in windows
        )
        result.avg_daily_pnl = total_net_profit / total_days if total_days > 0 else 0.0

        # Worst window return
        returns = [m.total_return_pct for m in test_metrics]
        result.worst_window_return_pct = min(returns) if returns else 0.0

        # Max drawdown (worst across all windows)
        drawdowns = [m.max_drawdown_pct for m in test_metrics]
        result.max_drawdown_pct = max(drawdowns) if drawdowns else 0.0

        # Check acceptance criteria
        result.passed = True
        rejections = []

        if result.aggregate_profit_factor < self.MIN_PROFIT_FACTOR:
            rejections.append(
                f"Profit factor {result.aggregate_profit_factor:.2f} < {self.MIN_PROFIT_FACTOR}"
            )
            result.passed = False

        if result.worst_window_return_pct < self.MAX_WORST_WINDOW_LOSS_PCT:
            rejections.append(
                f"Worst window {result.worst_window_return_pct:.2f}% < {self.MAX_WORST_WINDOW_LOSS_PCT}%"
            )
            result.passed = False

        if result.avg_daily_pnl < self.MIN_AVG_DAILY_PNL:
            rejections.append(
                f"Avg daily PnL ${result.avg_daily_pnl:.2f} < ${self.MIN_AVG_DAILY_PNL}"
            )
            result.passed = False

        if result.max_drawdown_pct > self.MAX_DRAWDOWN_PCT:
            rejections.append(
                f"Max drawdown {result.max_drawdown_pct:.2f}% > {self.MAX_DRAWDOWN_PCT}%"
            )
            result.passed = False

        if result.aggregate_trades < self.MIN_AGGREGATE_TRADES:
            rejections.append(
                f"Trades {result.aggregate_trades} < {self.MIN_AGGREGATE_TRADES} (insufficient significance)"
            )
            result.passed = False

        result.rejection_reasons = rejections
        return result
