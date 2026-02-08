"""Performance metrics calculator for backtesting results."""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import statistics


@dataclass
class BacktestMetrics:
    """Container for backtest performance metrics.

    Attributes:
        total_return_pct: Total return percentage
        net_profit_usd: Net profit in USD
        max_drawdown_pct: Maximum drawdown percentage
        profit_factor: Profit factor (gross profit / gross loss)
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate_pct: Win rate percentage
        avg_win_usd: Average winning trade PnL
        avg_loss_usd: Average losing trade PnL
        avg_trade_usd: Average trade PnL
        sharpe_ratio: Sharpe ratio (annualized)
        sortino_ratio: Sortino ratio (annualized)
        circuit_breaker_triggers: Number of circuit breaker triggers
        daily_lock_hits: Number of daily lock engagements
        start_equity: Starting equity
        end_equity: Ending equity
        start_time: Backtest start timestamp
        end_time: Backtest end timestamp
        equity_curve: List of (timestamp, equity) tuples
    """

    total_return_pct: float = 0.0
    net_profit_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0
    avg_trade_usd: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    circuit_breaker_triggers: int = 0
    daily_lock_hits: int = 0
    start_equity: float = 0.0
    end_equity: float = 0.0
    start_time: datetime | None = None
    end_time: datetime | None = None
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "total_return_pct": round(self.total_return_pct, 4),
            "net_profit_usd": round(self.net_profit_usd, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "max_drawdown_usd": round(self.max_drawdown_usd, 2),
            "profit_factor": round(self.profit_factor, 4),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": round(self.win_rate_pct, 2),
            "avg_win_usd": round(self.avg_win_usd, 2),
            "avg_loss_usd": round(self.avg_loss_usd, 2),
            "avg_trade_usd": round(self.avg_trade_usd, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "circuit_breaker_triggers": self.circuit_breaker_triggers,
            "daily_lock_hits": self.daily_lock_hits,
            "start_equity": round(self.start_equity, 2),
            "end_equity": round(self.end_equity, 2),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert metrics to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class MetricsCalculator:
    """Calculator for backtest performance metrics.

    Example:
        >>> calculator = MetricsCalculator(starting_equity=10000.0)
        >>> calculator.add_trade({"realized_pnl_usd": 150.0, ...})
        >>> calculator.add_equity_point(datetime.now(), 10150.0)
        >>> metrics = calculator.calculate()
    """

    def __init__(self, starting_equity: float = 10000.0):
        """Initialize metrics calculator.

        Args:
            starting_equity: Starting equity amount
        """
        self.starting_equity = starting_equity
        self.trades: list[dict[str, Any]] = []
        self.equity_curve: list[tuple[datetime, float]] = []
        self.returns: list[float] = []  # Period returns for Sharpe calculation
        self.circuit_breaker_triggers = 0
        self.daily_lock_hits = 0

    def add_trade(self, trade: dict[str, Any]) -> None:
        """Add a trade for analysis.

        Args:
            trade: Trade dictionary with realized_pnl_usd
        """
        self.trades.append(trade)

    def add_equity_point(self, timestamp: datetime, equity: float) -> None:
        """Add an equity data point.

        Args:
            timestamp: Timestamp of equity snapshot
            equity: Equity value
        """
        self.equity_curve.append((timestamp, equity))

    def set_safety_stats(self, breaker_triggers: int, daily_lock_hits: int) -> None:
        """Set safety mechanism statistics.

        Args:
            breaker_triggers: Number of circuit breaker triggers
            daily_lock_hits: Number of daily lock hits
        """
        self.circuit_breaker_triggers = breaker_triggers
        self.daily_lock_hits = daily_lock_hits

    def _calculate_return_metrics(self) -> tuple[float, float]:
        """Calculate total return and net profit.

        Returns:
            Tuple of (total_return_pct, net_profit_usd)
        """
        if not self.equity_curve:
            return 0.0, 0.0

        start_equity = self.starting_equity
        end_equity = self.equity_curve[-1][1]

        net_profit = end_equity - start_equity
        total_return_pct = (net_profit / start_equity) * 100.0 if start_equity > 0 else 0.0

        return total_return_pct, net_profit

    def _calculate_drawdown(self) -> tuple[float, float]:
        """Calculate maximum drawdown.

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_usd)
        """
        if not self.equity_curve:
            return 0.0, 0.0

        max_equity = self.starting_equity
        max_drawdown_pct = 0.0
        max_drawdown_usd = 0.0

        for _, equity in self.equity_curve:
            if equity > max_equity:
                max_equity = equity

            drawdown_usd = max_equity - equity
            drawdown_pct = (drawdown_usd / max_equity) * 100.0 if max_equity > 0 else 0.0

            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct
                max_drawdown_usd = drawdown_usd

        return max_drawdown_pct, max_drawdown_usd

    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor.

        Profit Factor = Gross Profit / Gross Loss

        Returns:
            Profit factor (0.0 if no losses)
        """
        gross_profit = sum(
            t.get("realized_pnl_usd", 0.0) or 0.0
            for t in self.trades
            if (t.get("realized_pnl_usd") or 0.0) > 0
        )
        gross_loss = abs(sum(
            t.get("realized_pnl_usd", 0.0) or 0.0
            for t in self.trades
            if (t.get("realized_pnl_usd") or 0.0) < 0
        ))

        if gross_loss == 0:
            return float(gross_profit) if gross_profit > 0 else 0.0

        return float(gross_profit / gross_loss)

    def _calculate_trade_stats(self) -> dict[str, Any]:
        """Calculate trade-related statistics.

        Returns:
            Dictionary with trade stats
        """
        closed_trades = [t for t in self.trades if t.get("status") == "CLOSED"]

        if not closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "avg_win_usd": 0.0,
                "avg_loss_usd": 0.0,
                "avg_trade_usd": 0.0,
            }

        total_trades = len(closed_trades)

        wins = [t for t in closed_trades if (t.get("realized_pnl_usd") or 0.0) > 0]
        losses = [t for t in closed_trades if (t.get("realized_pnl_usd") or 0.0) < 0]

        winning_trades = len(wins)
        losing_trades = len(losses)

        win_rate_pct = (winning_trades / total_trades) * 100.0 if total_trades > 0 else 0.0

        avg_win_usd = (
            sum(t.get("realized_pnl_usd", 0.0) or 0.0 for t in wins) / winning_trades
            if winning_trades > 0 else 0.0
        )
        avg_loss_usd = (
            sum(t.get("realized_pnl_usd", 0.0) or 0.0 for t in losses) / losing_trades
            if losing_trades > 0 else 0.0
        )
        avg_trade_usd = (
            sum(t.get("realized_pnl_usd", 0.0) or 0.0 for t in closed_trades) / total_trades
            if total_trades > 0 else 0.0
        )

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": win_rate_pct,
            "avg_win_usd": avg_win_usd,
            "avg_loss_usd": avg_loss_usd,
            "avg_trade_usd": avg_trade_usd,
        }

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sharpe ratio.

        Args:
            risk_free_rate: Annual risk-free rate (default: 0.0)

        Returns:
            Annualized Sharpe ratio
        """
        if len(self.equity_curve) < 2:
            return 0.0

        # Calculate period returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1][1]
            curr_equity = self.equity_curve[i][1]
            if prev_equity > 0:
                period_return = (curr_equity - prev_equity) / prev_equity
                returns.append(period_return)

        if len(returns) < 2:
            return 0.0

        # Calculate excess returns (subtract risk-free rate per period)
        # Assume 252 trading days per year, calculate per-period rf rate
        periods_per_year = 252 * 24 * 12  # Assuming 5-min periods (12 per hour)
        rf_per_period = risk_free_rate / periods_per_year

        excess_returns = [r - rf_per_period for r in returns]

        mean_excess = statistics.mean(excess_returns)
        std_excess = statistics.stdev(excess_returns) if len(excess_returns) > 1 else 0.0

        if std_excess == 0:
            return 0.0

        # Annualize
        sharpe = mean_excess / std_excess * math.sqrt(periods_per_year)
        return sharpe

    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sortino ratio.

        Uses downside deviation instead of standard deviation.

        Args:
            risk_free_rate: Annual risk-free rate (default: 0.0)

        Returns:
            Annualized Sortino ratio
        """
        if len(self.equity_curve) < 2:
            return 0.0

        # Calculate period returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1][1]
            curr_equity = self.equity_curve[i][1]
            if prev_equity > 0:
                period_return = (curr_equity - prev_equity) / prev_equity
                returns.append(period_return)

        if len(returns) < 2:
            return 0.0

        # Calculate excess returns
        periods_per_year = 252 * 24 * 12
        rf_per_period = risk_free_rate / periods_per_year

        excess_returns = [r - rf_per_period for r in returns]
        mean_excess = statistics.mean(excess_returns)

        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in excess_returns if r < 0]
        if not downside_returns:
            return float('inf') if mean_excess > 0 else 0.0

        downside_std = math.sqrt(sum(r ** 2 for r in downside_returns) / len(downside_returns))

        if downside_std == 0:
            return 0.0

        sortino = mean_excess / downside_std * math.sqrt(periods_per_year)
        return sortino

    def calculate(self) -> BacktestMetrics:
        """Calculate all metrics and return results.

        Returns:
            BacktestMetrics with all calculated values
        """
        total_return_pct, net_profit = self._calculate_return_metrics()
        max_drawdown_pct, max_drawdown_usd = self._calculate_drawdown()
        profit_factor = self._calculate_profit_factor()
        trade_stats = self._calculate_trade_stats()
        sharpe = self._calculate_sharpe_ratio()
        sortino = self._calculate_sortino_ratio()

        # Get start/end times
        start_time = self.equity_curve[0][0] if self.equity_curve else None
        end_time = self.equity_curve[-1][0] if self.equity_curve else None

        # Get final equity
        end_equity = self.equity_curve[-1][1] if self.equity_curve else self.starting_equity

        return BacktestMetrics(
            total_return_pct=total_return_pct,
            net_profit_usd=net_profit,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_usd=max_drawdown_usd,
            profit_factor=profit_factor,
            total_trades=trade_stats["total_trades"],
            winning_trades=trade_stats["winning_trades"],
            losing_trades=trade_stats["losing_trades"],
            win_rate_pct=trade_stats["win_rate_pct"],
            avg_win_usd=trade_stats["avg_win_usd"],
            avg_loss_usd=trade_stats["avg_loss_usd"],
            avg_trade_usd=trade_stats["avg_trade_usd"],
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            circuit_breaker_triggers=self.circuit_breaker_triggers,
            daily_lock_hits=self.daily_lock_hits,
            start_equity=self.starting_equity,
            end_equity=end_equity,
            start_time=start_time,
            end_time=end_time,
            equity_curve=self.equity_curve,
            trades=self.trades,
        )
