"""Backtesting framework for Quantsail trading engine.

This module provides a realistic backtesting environment that executes
actual production engine code against historical market data.

Key Components:
    - BacktestMarketProvider: Simulated market data feed
    - BacktestExecutor: Simulated order execution with slippage and fees
    - BacktestRepository: In-memory SQLite storage for backtest data
    - TimeManager: Simulated time control for deterministic testing
    - BacktestTradingLoop: Historical data iteration runner
    - MetricsCalculator: Performance analytics (Sharpe, Drawdown, etc.)

Example:
    >>> from quantsail_engine.backtest import BacktestRunner
    >>> runner = BacktestRunner(config, data_file="BTC_USDT_1m.csv")
    >>> results = runner.run()
    >>> print(f"Total Return: {results.total_return_pct:.2f}%")
"""

from quantsail_engine.backtest.executor import BacktestExecutor
from quantsail_engine.backtest.market_provider import BacktestMarketProvider
from quantsail_engine.backtest.metrics import BacktestMetrics, MetricsCalculator
from quantsail_engine.backtest.monte_carlo import MonteCarloResult, MonteCarloSimulator
from quantsail_engine.backtest.repository import BacktestRepository
from quantsail_engine.backtest.runner import BacktestRunner
from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.backtest.walk_forward import WalkForwardAnalyzer, WFAResult

__all__ = [
    "BacktestExecutor",
    "BacktestMarketProvider",
    "BacktestMetrics",
    "BacktestRepository",
    "BacktestRunner",
    "MetricsCalculator",
    "MonteCarloResult",
    "MonteCarloSimulator",
    "TimeManager",
    "WalkForwardAnalyzer",
    "WFAResult",
]
