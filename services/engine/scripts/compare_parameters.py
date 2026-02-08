"""Compare backtest performance across parameter profiles.

Runs BacktestRunner with the default config, then with each preset
profile (conservative, moderate, aggressive). Produces a JSON comparison
report saved to backtest_results/.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quantsail_engine.backtest.metrics import BacktestMetrics
from quantsail_engine.backtest.runner import BacktestRunner
from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile, list_profiles

# ── defaults ──────────────────────────────────────────────────────────
DEFAULT_DATA_FILE = "data/historical/BTCUSDT_5m.csv"
DEFAULT_OUTPUT_DIR = "backtest_results"
DEFAULT_STARTING_CASH = 10_000.0
DEFAULT_SLIPPAGE_PCT = 0.05
DEFAULT_FEE_PCT = 0.1


def _metrics_summary(metrics: BacktestMetrics) -> dict[str, Any]:
    """Extract the key comparison fields from BacktestMetrics."""
    return {
        "net_profit_usd": round(metrics.net_profit_usd, 2),
        "total_return_pct": round(metrics.total_return_pct, 4),
        "sharpe_ratio": round(metrics.sharpe_ratio, 4),
        "sortino_ratio": round(metrics.sortino_ratio, 4),
        "max_drawdown_pct": round(metrics.max_drawdown_pct, 4),
        "max_drawdown_usd": round(metrics.max_drawdown_usd, 2),
        "profit_factor": round(metrics.profit_factor, 4),
        "win_rate_pct": round(metrics.win_rate_pct, 2),
        "total_trades": metrics.total_trades,
        "winning_trades": metrics.winning_trades,
        "losing_trades": metrics.losing_trades,
        "avg_trade_usd": round(metrics.avg_trade_usd, 2),
        "circuit_breaker_triggers": metrics.circuit_breaker_triggers,
        "daily_lock_hits": metrics.daily_lock_hits,
        "start_equity": round(metrics.start_equity, 2),
        "end_equity": round(metrics.end_equity, 2),
    }


def run_backtest(
    config: BotConfig,
    data_file: str | Path,
    label: str,
    *,
    starting_cash: float = DEFAULT_STARTING_CASH,
    slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
    fee_pct: float = DEFAULT_FEE_PCT,
) -> dict[str, Any]:
    """Run a single backtest and return a summary dict."""
    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"{'='*60}")

    runner = BacktestRunner(
        config=config,
        data_file=data_file,
        starting_cash=starting_cash,
        slippage_pct=slippage_pct,
        fee_pct=fee_pct,
    )
    try:
        metrics = runner.run()
    finally:
        runner.close()

    summary = _metrics_summary(metrics)
    summary["label"] = label
    return summary


def compare_profiles(
    data_file: str | Path = DEFAULT_DATA_FILE,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    starting_cash: float = DEFAULT_STARTING_CASH,
) -> dict[str, Any]:
    """Run backtests for default config and each profile, return comparison."""
    data_path = Path(data_file)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Historical data file not found: {data_path}. "
            "Download OHLCV data first (e.g., BTCUSDT_5m.csv)."
        )

    base_config = BotConfig()
    results: list[dict[str, Any]] = []

    # 1) Default (untuned) config
    results.append(
        run_backtest(base_config, data_path, "default", starting_cash=starting_cash)
    )

    # 2) Each named profile
    for profile_name in list_profiles():
        tuned_dict = apply_profile(base_config.model_dump(), profile_name)
        tuned_config = BotConfig(**tuned_dict)
        results.append(
            run_backtest(
                tuned_config, data_path, profile_name, starting_cash=starting_cash
            )
        )

    # Build comparison report
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_file": str(data_path),
        "starting_cash": starting_cash,
        "profiles_compared": [r["label"] for r in results],
        "results": results,
    }

    # Save to disk
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = output_path / "parameter_comparison.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Comparison saved to: {report_file}")
    print(f"{'='*60}")

    # Print summary table
    _print_summary_table(results)

    return report


def _print_summary_table(results: list[dict[str, Any]]) -> None:
    """Print a formatted comparison table to stdout."""
    metrics_keys = [
        ("net_profit_usd", "Net P&L ($)"),
        ("total_return_pct", "Return (%)"),
        ("sharpe_ratio", "Sharpe"),
        ("sortino_ratio", "Sortino"),
        ("max_drawdown_pct", "Max DD (%)"),
        ("profit_factor", "Profit Factor"),
        ("win_rate_pct", "Win Rate (%)"),
        ("total_trades", "Total Trades"),
    ]

    # Header
    header = f"{'Metric':<20}"
    for r in results:
        header += f" | {r['label']:>14}"
    print(f"\n{header}")
    print("-" * len(header))

    # Rows
    for key, label in metrics_keys:
        row = f"{label:<20}"
        for r in results:
            val = r.get(key, "N/A")
            if isinstance(val, float):
                row += f" | {val:>14.4f}"
            else:
                row += f" | {val:>14}"
        print(row)


if __name__ == "__main__":
    data = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA_FILE
    compare_profiles(data_file=data)
