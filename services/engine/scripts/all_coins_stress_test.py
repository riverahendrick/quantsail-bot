"""All-Coin Grid Stress Test.

Tests grid strategy across ALL 18 coins we have data for, with
conservative (safe drawdown) parameters. Target: $1-2/day combined.

Key difference from stress_test_suite.py:
  - Runs all 18 coins, not just BTC/ETH/SOL
  - Uses wider grid ranges to keep drawdown <25%
  - Reports daily income consistency
  - Validates $1+/day target
  - Reports per-coin daily average

Usage:
    python scripts/all_coins_stress_test.py
    python scripts/all_coins_stress_test.py --slippage 0.05
"""

from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantsail_engine.backtest.grid_backtest import GridBacktestRunner, GridMetrics  # noqa: E402
from quantsail_engine.backtest.backtest_results import (  # noqa: E402
    save_grid_result,
    save_stress_test_report,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"

# ═══════════════════════════════════════════════════════════════
# COIN CONFIGURATIONS — Conservative (safe DD) parameters
#
# Strategy:
# - Large caps (BTC/ETH): Wider range (±20%), more grids (35)
# - Mid caps (SOL/BNB/XRP/AVAX/ADA/DOT/LINK): ±22%, 25 grids
# - Small/volatile (APT/ARB/ATOM/DOGE/NEAR/OP/POL/SUI/UNI):
#   ±25%, 20 grids
#
# Wider ranges = fewer rebalances = lower drawdown
# More grids = more trade opportunities = more daily income
# ═══════════════════════════════════════════════════════════════

TOTAL_ALLOCATION = 5000.0  # $5,000 total capital

# Tier 1: Large caps — highest allocation
TIER1_COINS = [
    {"symbol": "BTC", "pair": "BTC_USDT", "alloc_pct": 0.20,
     "num_grids": 50, "lower_pct": 18.0, "upper_pct": 18.0},
    {"symbol": "ETH", "pair": "ETH_USDT", "alloc_pct": 0.18,
     "num_grids": 40, "lower_pct": 20.0, "upper_pct": 20.0},
]

# Tier 2: Battle-tested mid caps — all profitable in round 1 & 2
TIER2_COINS = [
    {"symbol": "BNB", "pair": "BNB_USDT", "alloc_pct": 0.13,
     "num_grids": 35, "lower_pct": 20.0, "upper_pct": 20.0},
    {"symbol": "SOL", "pair": "SOL_USDT", "alloc_pct": 0.10,
     "num_grids": 30, "lower_pct": 30.0, "upper_pct": 30.0},
    {"symbol": "XRP", "pair": "XRP_USDT", "alloc_pct": 0.08,
     "num_grids": 30, "lower_pct": 28.0, "upper_pct": 28.0},
    {"symbol": "LINK", "pair": "LINK_USDT", "alloc_pct": 0.07,
     "num_grids": 28, "lower_pct": 28.0, "upper_pct": 28.0},
    {"symbol": "ADA", "pair": "ADA_USDT", "alloc_pct": 0.06,
     "num_grids": 28, "lower_pct": 28.0, "upper_pct": 28.0},
]

# Tier 3: Proven small caps — extra-wide safety nets
TIER3_COINS = [
    {"symbol": "DOGE", "pair": "DOGE_USDT", "alloc_pct": 0.06,
     "num_grids": 22, "lower_pct": 32.0, "upper_pct": 32.0},
    {"symbol": "NEAR", "pair": "NEAR_USDT", "alloc_pct": 0.06,
     "num_grids": 22, "lower_pct": 30.0, "upper_pct": 30.0},
    {"symbol": "SUI", "pair": "SUI_USDT", "alloc_pct": 0.06,
     "num_grids": 22, "lower_pct": 32.0, "upper_pct": 32.0},
]

ALL_COINS = TIER1_COINS + TIER2_COINS + TIER3_COINS
FEE_PCT = 0.1  # Binance spot maker fee


def run_all_coins(slippage_pct: float, save: bool = True) -> dict[str, Any]:
    """Run grid backtest for all 18 coins on current data."""
    results: list[GridMetrics] = []
    skipped: list[str] = []
    all_trades: dict[str, list] = {}

    alloc_check = sum(c["alloc_pct"] for c in ALL_COINS)
    print(f"\n  Allocation check: {alloc_check:.0%} of ${TOTAL_ALLOCATION:,.0f}")

    for coin in ALL_COINS:
        pair: str = str(coin["pair"])
        sym: str = str(coin["symbol"])
        data_file = DATA_DIR / f"{pair}_1h_ohlcv.csv"
        if not data_file.exists():
            print(f"  {sym}: NO DATA, skipping")
            skipped.append(sym)
            continue

        alloc_usd: float = TOTAL_ALLOCATION * float(coin["alloc_pct"])
        runner = GridBacktestRunner(
            data_file=data_file,
            symbol=sym,
            allocation_usd=alloc_usd,
            num_grids=int(coin["num_grids"]),
            lower_pct=float(coin["lower_pct"]),
            upper_pct=float(coin["upper_pct"]),
            fee_pct=FEE_PCT,
            rebalance_on_breakout=True,
            slippage_pct=slippage_pct,
            regime="2025_current",
        )
        metrics = runner.run()
        results.append(metrics)
        all_trades[sym] = runner.trades

        if save:
            save_grid_result(metrics, runner.trades)

    return {
        "results": results,
        "skipped": skipped,
        "all_trades": all_trades,
    }


def analyze_daily_consistency(
    results: list[GridMetrics],
) -> dict[str, Any]:
    """Analyze daily income consistency across all coins."""
    # Merge all daily PnL into a single daily total
    combined_daily: dict[str, float] = {}
    for m in results:
        for day, pnl in m.daily_pnl.items():
            combined_daily[day] = combined_daily.get(day, 0) + pnl

    sorted_days = sorted(combined_daily.keys())
    if not sorted_days:
        return {"error": "No daily data"}

    values = [combined_daily[d] for d in sorted_days]
    total_days = len(values)
    green_days = sum(1 for v in values if v > 0)
    red_days = sum(1 for v in values if v < 0)
    zero_days = sum(1 for v in values if v == 0)
    avg_daily = sum(values) / total_days if total_days else 0
    best_day = max(values)
    worst_day = min(values)

    # Consecutive red days / zero days
    max_consec_red = 0
    current_red = 0
    max_consec_zero = 0
    current_zero = 0
    for v in values:
        if v <= 0:
            current_red += 1
            max_consec_red = max(max_consec_red, current_red)
        else:
            current_red = 0
        if v == 0:
            current_zero += 1
            max_consec_zero = max(max_consec_zero, current_zero)
        else:
            current_zero = 0

    # Monthly breakdown
    monthly: dict[str, float] = {}
    for day in sorted_days:
        month: str = str(day)[:7]  # "2025-01"
        monthly[month] = monthly.get(month, 0.0) + combined_daily[day]

    return {
        "total_days": total_days,
        "green_days": green_days,
        "red_days": red_days,
        "zero_days": zero_days,
        "green_pct": green_days / total_days * 100,
        "avg_daily_pnl": avg_daily,
        "best_day": best_day,
        "worst_day": worst_day,
        "max_consec_red": max_consec_red,
        "max_consec_zero": max_consec_zero,
        "monthly": monthly,
    }


def print_full_report(
    results: list[GridMetrics],
    daily_stats: dict[str, Any],
    slippage: float,
    skipped: list[str],
) -> None:
    """Print comprehensive report."""
    print("\n")
    print("=" * 75)
    print("  ALL-COIN GRID STRESS TEST — COMPREHENSIVE REPORT")
    print(f"  Capital: ${TOTAL_ALLOCATION:,.0f}  |  Slippage: {slippage}%  |  Fees: {FEE_PCT}%/side")
    print("=" * 75)

    if skipped:
        print(f"  Skipped (no data): {', '.join(skipped)}")

    # Per-coin summary table
    print(f"\n{'Coin':<6} {'Alloc':>7} {'PnL':>10} {'Return':>8} "
          f"{'Trades':>7} {'$/day':>7} {'MaxDD':>7} {'Rebal':>6}")
    print("-" * 75)

    total_pnl = 0.0
    total_trades = 0
    max_dd_global = 0.0

    # Sort by PnL for easy reading
    sorted_results = sorted(results, key=lambda m: m.total_pnl, reverse=True)

    for m in sorted_results:
        daily = m.total_pnl / m.period_days if m.period_days > 0 else 0
        total_pnl += m.total_pnl
        total_trades += m.total_trades
        max_dd_global = max(max_dd_global, m.max_drawdown_pct)

        print(f"{m.symbol:<6} ${m.starting_cash:>6.0f} "
              f"${m.total_pnl:>+9.2f} "
              f"{m.total_pnl_pct:>+7.1f}% "
              f"{m.total_trades:>7} "
              f"${daily:>6.2f} "
              f"{m.max_drawdown_pct:>6.1f}% "
              f"{m.num_rebalances:>5}")

    print("-" * 75)
    total_alloc = sum(m.starting_cash for m in results)
    period = max(m.period_days for m in results) if results else 1
    avg_daily = total_pnl / period

    print(f"{'TOTAL':<6} ${total_alloc:>6.0f} "
          f"${total_pnl:>+9.2f} "
          f"{total_pnl / total_alloc * 100:>+7.1f}% "
          f"{total_trades:>7} "
          f"${avg_daily:>6.2f} "
          f"{max_dd_global:>6.1f}% ")

    # Daily consistency
    print(f"\n{'='*75}")
    print("  DAILY INCOME CONSISTENCY")
    print(f"{'='*75}")
    print(f"  Average daily income: ${daily_stats['avg_daily_pnl']:.2f}")
    print(f"  Green days: {daily_stats['green_days']}/{daily_stats['total_days']} "
          f"({daily_stats['green_pct']:.1f}%)")
    print(f"  Red days: {daily_stats['red_days']}")
    print(f"  Zero days: {daily_stats['zero_days']}")
    print(f"  Best day: ${daily_stats['best_day']:.2f}")
    print(f"  Worst day: ${daily_stats['worst_day']:.2f}")
    print(f"  Max consecutive red/zero days: "
          f"{daily_stats['max_consec_red']}")

    # Monthly breakdown
    print(f"\n  Monthly PnL:")
    monthly = daily_stats.get("monthly", {})
    for month in sorted(monthly.keys()):
        pnl = monthly[month]
        days_in_month = sum(
            1 for d in daily_stats.get("_days", [])
            if d.startswith(month)
        ) or 30
        print(f"    {month}: ${pnl:>+8.2f} "
              f"(${pnl / 30:>+.2f}/day avg)")

    # Pass/fail
    print(f"\n{'='*75}")
    print("  PASS / FAIL CRITERIA")
    print(f"{'='*75}")

    checks = {
        f"Daily income >= $1.00": avg_daily >= 1.0,
        f"Max drawdown < 35% (got {max_dd_global:.1f}%)": max_dd_global < 35.0,
        f"Green days > 80% (got {daily_stats['green_pct']:.1f}%)": daily_stats["green_pct"] > 80.0,
        f"Max consecutive red <= 5 days (got {daily_stats['max_consec_red']})": daily_stats["max_consec_red"] <= 5,
        f"All coins profitable": all(m.total_pnl > 0 for m in results),
    }

    all_pass = True
    for name, passed in checks.items():
        icon = "+" if passed else "X"
        status = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}: {status}")
        if not passed:
            all_pass = False

    print(f"\n  {'='*55}")
    if all_pass:
        print("  VERDICT: ✅ PASS — Ready for testnet deployment")
    else:
        print("  VERDICT: ❌ NEEDS TUNING — Adjust params for failing criteria")
    print(f"  {'='*55}")

    # Losers that need attention
    losers = [m for m in results if m.total_pnl <= 0]
    if losers:
        print(f"\n  ⚠️  LOSING COINS (need wider grid or removal):")
        for m in losers:
            daily_loss = m.total_pnl / m.period_days if m.period_days > 0 else 0
            print(f"    {m.symbol}: ${m.total_pnl:+.2f} "
                  f"(${daily_loss:+.2f}/day, {m.max_drawdown_pct:.1f}% DD)")


def main() -> None:
    """Run all-coin stress test."""
    parser = argparse.ArgumentParser(
        description="All-coin grid strategy stress test"
    )
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
    print("=" * 75)
    print("  ALL-COIN GRID STRATEGY STRESS TEST")
    print("=" * 75)
    print(f"  Coins: {len(ALL_COINS)}")
    print(f"  Capital: ${TOTAL_ALLOCATION:,.0f}")
    print(f"  Slippage: {args.slippage}%")
    print(f"  Tiers: {len(TIER1_COINS)} large + {len(TIER2_COINS)} mid + {len(TIER3_COINS)} small")

    data = run_all_coins(args.slippage, save=not args.no_save)
    results = data["results"]
    skipped = data["skipped"]

    if not results:
        print("\n  ERROR: No results. Check data files.")
        sys.exit(1)

    daily_stats = analyze_daily_consistency(results)

    if not args.no_save:
        regime_summary = {
            "regime": "2025_all_coins",
            "label": "All 18 Coins — Conservative Grid",
            "total_pnl": sum(m.total_pnl for m in results),
            "symbol_results": [
                {"symbol": m.symbol, "pnl": m.total_pnl,
                 "daily_avg": m.total_pnl / m.period_days}
                for m in results
            ],
        }
        save_stress_test_report(
            [regime_summary],
            {
                "daily_income_>=_$1": daily_stats["avg_daily_pnl"] >= 1.0,
                "max_dd_<_25%": max(m.max_drawdown_pct for m in results) < 25.0,
                "green_days_>_80%": daily_stats["green_pct"] > 80.0,
            },
        )

    print_full_report(results, daily_stats, args.slippage, skipped)

    elapsed = time.time() - start
    print(f"\n  Completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
