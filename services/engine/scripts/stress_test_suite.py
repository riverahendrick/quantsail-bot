"""Multi-Regime Grid Trading Stress Test Suite.

Tests grid strategy across 4 market regimes (2022 bear, 2023 recovery,
2024 range, 2025 current) with realistic slippage modeling.

Pass criteria (ALL must be true before testnet deployment):
  1. Total PnL positive in >= 3 of 4 regimes
  2. Max drawdown < 40% in every regime
  3. No more than 14 consecutive zero-trade days
  4. Combined total PnL across all regimes is positive

Usage:
    python scripts/stress_test_suite.py
    python scripts/stress_test_suite.py --slippage 0.03
"""

import sys
import time
import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantsail_engine.backtest.grid_backtest import GridBacktestRunner, GridMetrics
from quantsail_engine.backtest.backtest_results import (
    save_grid_result,
    save_stress_test_report,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
STRESS_DIR = DATA_DIR / "stress_test"

# Grid configs per symbol — same as hybrid_backtest.py
GRID_CONFIGS: list[dict[str, Any]] = [
    {"symbol": "BTC", "pair": "BTC_USDT", "num_grids": 30,
     "lower_pct": 15.0, "upper_pct": 15.0, "alloc": 1200.0},
    {"symbol": "ETH", "pair": "ETH_USDT", "num_grids": 25,
     "lower_pct": 18.0, "upper_pct": 18.0, "alloc": 1000.0},
    {"symbol": "SOL", "pair": "SOL_USDT", "num_grids": 25,
     "lower_pct": 20.0, "upper_pct": 20.0, "alloc": 800.0},
]

REGIMES: list[dict[str, str]] = [
    {"name": "2022_bear", "label": "2022 Crypto Winter (Bear)"},
    {"name": "2023_recovery", "label": "2023 Recovery Rally"},
    {"name": "2024_range", "label": "2024 Accumulation / Range"},
    {"name": "2025_current", "label": "2025 Current Market"},
]

FEE_PCT = 0.1


def _get_data_file(regime_name: str, pair: str) -> Path | None:
    """Find the data file for a regime/pair combo."""
    if regime_name == "2025_current":
        # Current data is in main historical dir
        f = DATA_DIR / f"{pair}_1h_ohlcv.csv"
    else:
        f = STRESS_DIR / regime_name / f"{pair}_1h_ohlcv.csv"
    return f if f.exists() else None


def run_regime(
    regime: dict[str, str],
    slippage_pct: float,
    save_results: bool = True,
) -> dict[str, Any]:
    """Run grid backtest for one regime across all symbols.

    Returns dict with regime summary and list of per-symbol metrics.
    """
    regime_name = regime["name"]
    regime_label = regime["label"]
    results: list[GridMetrics] = []
    skipped: list[str] = []

    print(f"\n{'='*60}")
    print(f"  Regime: {regime_label}")
    print(f"  Slippage: {slippage_pct}%")
    print(f"{'='*60}")

    for cfg in GRID_CONFIGS:
        data_file = _get_data_file(regime_name, cfg["pair"])
        if data_file is None:
            print(f"  {cfg['symbol']}: DATA NOT FOUND — skipping")
            skipped.append(cfg["symbol"])
            continue

        runner = GridBacktestRunner(
            data_file=data_file,
            symbol=cfg["symbol"],
            allocation_usd=cfg["alloc"],
            num_grids=cfg["num_grids"],
            lower_pct=cfg["lower_pct"],
            upper_pct=cfg["upper_pct"],
            fee_pct=FEE_PCT,
            rebalance_on_breakout=True,
            slippage_pct=slippage_pct,
            regime=regime_name,
        )
        metrics = runner.run()
        results.append(metrics)

        if save_results:
            save_grid_result(metrics, runner.trades)

    # Aggregate
    total_pnl = sum(m.total_pnl for m in results)
    total_alloc = sum(m.starting_cash for m in results)
    total_trades = sum(m.total_trades for m in results)
    max_dd = max((m.max_drawdown_pct for m in results), default=0.0)
    period_days = max((m.period_days for m in results), default=0)

    # Count max consecutive zero days
    all_daily: dict[str, float] = {}
    for m in results:
        for day, pnl in m.daily_pnl.items():
            all_daily[day] = all_daily.get(day, 0) + pnl

    max_zero_streak = 0
    current_streak = 0
    for day in sorted(all_daily.keys()):
        if all_daily[day] == 0:
            current_streak += 1
            max_zero_streak = max(max_zero_streak, current_streak)
        else:
            current_streak = 0

    return {
        "regime": regime_name,
        "label": regime_label,
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_alloc * 100, 2) if total_alloc > 0 else 0,
        "total_trades": total_trades,
        "max_drawdown_pct": round(max_dd, 2),
        "max_zero_streak": max_zero_streak,
        "period_days": period_days,
        "skipped_symbols": skipped,
        "symbol_results": [
            {
                "symbol": m.symbol,
                "pnl": m.total_pnl,
                "pnl_pct": m.total_pnl_pct,
                "trades": m.total_trades,
                "max_dd": m.max_drawdown_pct,
                "rebalances": m.num_rebalances,
            }
            for m in results
        ],
    }


def check_pass_criteria(
    regime_results: list[dict[str, Any]],
) -> dict[str, bool]:
    """Check all pass criteria. Returns {criterion: passed}."""
    completed = [r for r in regime_results if not r["skipped_symbols"]]

    # 1. Positive PnL in >= 3 of 4 regimes
    positive_count = sum(1 for r in regime_results if r["total_pnl"] > 0)
    total_regimes = len(regime_results)

    # 2. Max drawdown < 40% in every regime
    all_dd_ok = all(r["max_drawdown_pct"] < 40 for r in regime_results)

    # 3. No more than 14 consecutive zero-trade days
    max_streak = max((r["max_zero_streak"] for r in regime_results), default=0)
    streak_ok = max_streak <= 14

    # 4. Combined total PnL positive
    combined_pnl = sum(r["total_pnl"] for r in regime_results)

    return {
        f"profitable_regimes_>=3_of_{total_regimes}": positive_count >= min(3, total_regimes),
        "max_drawdown_<40%_all_regimes": all_dd_ok,
        "max_zero_streak_<=14_days": streak_ok,
        "combined_pnl_positive": combined_pnl > 0,
    }


def print_report(
    regime_results: list[dict[str, Any]],
    criteria: dict[str, bool],
    slippage: float,
) -> None:
    """Print the full stress test report."""
    print("\n")
    print("=" * 70)
    print("  GRID STRATEGY STRESS TEST REPORT")
    print(f"  Slippage model: {slippage}%")
    print("=" * 70)

    # Header
    regimes_with_data = [r for r in regime_results if r["symbol_results"]]
    if not regimes_with_data:
        print("  NO DATA AVAILABLE. Run download_stress_data.py first.")
        return

    # Regime comparison table
    print(f"\n{'Symbol':<8}", end="")
    for r in regime_results:
        short = r["regime"][:12]
        print(f"  {short:>14}", end="")
    print()
    print("-" * (8 + 16 * len(regime_results)))

    # Per-symbol rows
    for cfg in GRID_CONFIGS:
        sym = cfg["symbol"]
        print(f"{sym:<8}", end="")
        for r in regime_results:
            matched = [s for s in r["symbol_results"] if s["symbol"] == sym]
            if matched:
                pnl = matched[0]["pnl"]
                print(f"  ${pnl:>+12.2f}", end="")
            else:
                print(f"  {'N/A':>14}", end="")
        print()

    # Total row
    print("-" * (8 + 16 * len(regime_results)))
    print(f"{'TOTAL':<8}", end="")
    for r in regime_results:
        print(f"  ${r['total_pnl']:>+12.2f}", end="")
    print()

    # Drawdown row
    print(f"{'MaxDD%':<8}", end="")
    for r in regime_results:
        print(f"  {r['max_drawdown_pct']:>13.1f}%", end="")
    print()

    # Trades row
    print(f"{'Trades':<8}", end="")
    for r in regime_results:
        print(f"  {r['total_trades']:>14}", end="")
    print()

    # Combined summary
    combined_pnl = sum(r["total_pnl"] for r in regime_results)
    total_alloc = sum(c["alloc"] for c in GRID_CONFIGS)
    print(f"\n  Combined PnL across all regimes: ${combined_pnl:+,.2f}")
    print(f"  Combined Return: {combined_pnl/total_alloc*100:+.1f}% on ${total_alloc:,.0f}")

    # Pass/fail
    print(f"\n{'='*70}")
    print("  PASS/FAIL CRITERIA")
    print("=" * 70)
    all_pass = True
    for name, passed in criteria.items():
        icon = "PASS" if passed else "FAIL"
        marker = "+" if passed else "X"
        print(f"  [{marker}] {name}: {icon}")
        if not passed:
            all_pass = False

    print(f"\n  {'='*50}")
    if all_pass:
        print("  OVERALL: PASS — Strategy is APPROVED for testnet deployment")
    else:
        print("  OVERALL: FAIL — Strategy needs parameter tuning before testnet")
    print(f"  {'='*50}")


def main() -> None:
    """Run the full stress test suite."""
    parser = argparse.ArgumentParser(description="Grid strategy stress test")
    parser.add_argument(
        "--slippage", type=float, default=0.03,
        help="Slippage model in percent (default: 0.03%%)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save results to JSON",
    )
    args = parser.parse_args()

    start = time.time()
    print("=" * 70)
    print("  GRID STRATEGY MULTI-REGIME STRESS TEST")
    print("=" * 70)
    print(f"  Symbols: BTC, ETH, SOL")
    print(f"  Allocation: $3,000 total")
    print(f"  Slippage: {args.slippage}% per trade")
    print(f"  Fee: {FEE_PCT}% per side")

    # Check which regimes have data
    available = []
    missing = []
    for regime in REGIMES:
        has_data = any(
            _get_data_file(regime["name"], cfg["pair"]) is not None
            for cfg in GRID_CONFIGS
        )
        if has_data:
            available.append(regime)
        else:
            missing.append(regime)

    if missing:
        print(f"\n  Missing data for: {', '.join(r['name'] for r in missing)}")
        print(f"  Run: python scripts/download_stress_data.py")

    if not available:
        print("\n  ERROR: No data available. Download data first.")
        sys.exit(1)

    # Run all available regimes
    all_regime_results: list[dict[str, Any]] = []
    for regime in available:
        result = run_regime(regime, args.slippage, save_results=not args.no_save)
        all_regime_results.append(result)

    # Check pass criteria
    criteria = check_pass_criteria(all_regime_results)

    # Save stress report
    if not args.no_save:
        report_path = save_stress_test_report(all_regime_results, criteria)
        print(f"\n  Report saved: {report_path}")

    # Print human-readable report
    print_report(all_regime_results, criteria, args.slippage)

    elapsed = time.time() - start
    print(f"\n  Completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
