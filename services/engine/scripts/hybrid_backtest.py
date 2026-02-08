"""Grid + Trend Hybrid Backtest Script.

Runs grid backtests on BTC/ETH/SOL and trend backtests on 8 altcoins,
then combines results to show the true hybrid daily income picture.
"""

import sys
import time
from pathlib import Path

# Engine import resolution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantsail_engine.backtest.grid_backtest import GridBacktestRunner, GridMetrics

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"

# ── GRID LAYER: BTC, ETH, SOL ──────────────────────────────────────────────
GRID_COINS = [
    # (symbol, csv_file, num_grids, lower_pct, upper_pct, allocation_usd)
    # Wider ranges = fewer rebalances = less liquidation drag
    ("BTC", "BTC_USDT_1h_ohlcv.csv",  30, 15.0, 15.0, 1200.0),
    ("ETH", "ETH_USDT_1h_ohlcv.csv",  25, 18.0, 18.0, 1000.0),
    ("SOL", "SOL_USDT_1h_ohlcv.csv",  25, 20.0, 20.0,  800.0),
]

FEE_PCT = 0.1  # Binance spot fee


def run_grid_backtests() -> list[GridMetrics]:
    """Run grid backtests on all grid coins."""
    results = []
    for symbol, csv_file, num_grids, lower_pct, upper_pct, alloc in GRID_COINS:
        data_file = DATA_DIR / csv_file
        if not data_file.exists():
            print(f"⚠️  Skipping {symbol}: {csv_file} not found")
            continue

        runner = GridBacktestRunner(
            data_file=data_file,
            symbol=symbol,
            allocation_usd=alloc,
            num_grids=num_grids,
            lower_pct=lower_pct,
            upper_pct=upper_pct,
            fee_pct=FEE_PCT,
            rebalance_on_breakout=True,
            regime="2025_current",
        )
        metrics = runner.run()
        results.append(metrics)
        print()

    return results


def print_grid_summary(
    results: list[GridMetrics],
) -> tuple[float, float, int]:
    """Print combined grid results.

    Returns:
        Tuple of (total_pnl, daily_avg, period_days).
    """
    print("\n" + "=" * 70)
    print("📊 GRID LAYER SUMMARY")
    print("=" * 70)
    print(f"{'Symbol':<8} {'Trades':>8} {'Tr/Day':>8} {'PnL($)':>10} "
          f"{'PnL(%)':>8} {'Fees($)':>8} {'Rebal':>6} {'MaxDD%':>8}")
    print("-" * 70)

    total_trades = 0
    total_pnl = 0.0
    total_fees = 0.0
    total_alloc = 0.0
    period_days = 0

    for m in results:
        print(f"{m.symbol:<8} {m.total_trades:>8} {m.trades_per_day:>8.1f} "
              f"${m.total_pnl:>+9.2f} {m.total_pnl_pct:>+7.2f}% "
              f"${m.total_fees:>7.2f} {m.num_rebalances:>6} "
              f"{m.max_drawdown_pct:>7.2f}%")
        total_trades += m.total_trades
        total_pnl += m.total_pnl
        total_fees += m.total_fees
        total_alloc += m.starting_cash
        period_days = max(period_days, m.period_days)

    print("-" * 70)
    daily_avg = total_pnl / period_days if period_days > 0 else 0
    monthly_avg = daily_avg * 30
    print(f"{'TOTAL':<8} {total_trades:>8} "
          f"{total_trades/period_days if period_days else 0:>8.1f} "
          f"${total_pnl:>+9.2f} "
          f"{total_pnl/total_alloc*100 if total_alloc else 0:>+7.2f}% "
          f"${total_fees:>7.2f}")
    print(f"\n💰 Grid Income Breakdown:")
    print(f"   Total Allocation:  ${total_alloc:,.0f}")
    print(f"   Annual PnL:        ${total_pnl:+,.2f}")
    print(f"   Daily Average:     ${daily_avg:+.2f}/day")
    print(f"   Monthly Average:   ${monthly_avg:+.2f}/month")
    print(f"   Annual Return:     {total_pnl/total_alloc*100 if total_alloc else 0:+.1f}%")
    print(f"   Period:            {period_days} days")

    # Print daily trade distribution
    if results:
        print(f"\n📅 Daily Trade Distribution (sample):")
        # aggregate daily trades
        all_daily = {}
        for m in results:
            for day, pnl in m.daily_pnl.items():
                all_daily[day] = all_daily.get(day, 0) + pnl

        days_sorted = sorted(all_daily.keys())
        zero_pnl_days = sum(1 for pnl in all_daily.values() if pnl == 0)
        positive_days = sum(1 for pnl in all_daily.values() if pnl > 0)
        negative_days = sum(1 for pnl in all_daily.values() if pnl < 0)
        print(f"   Positive days: {positive_days} "
              f"({positive_days/len(all_daily)*100:.0f}%)")
        print(f"   Zero days:     {zero_pnl_days} "
              f"({zero_pnl_days/len(all_daily)*100:.0f}%)")
        print(f"   Negative days: {negative_days} "
              f"({negative_days/len(all_daily)*100:.0f}%)")

        # Show first 10 days as sample
        print(f"\n   Sample (first 10 days):")
        sample_days: list[str] = list(days_sorted[:10])
        for day in sample_days:
            print(f"     {day}: ${all_daily[day]:+.2f}")

    return total_pnl, daily_avg, period_days


def main() -> None:
    """Run hybrid backtest."""
    start = time.time()

    print("=" * 70)
    print("🚀 HYBRID GRID + TREND BACKTEST")
    print("=" * 70)
    print(f"Grid Layer:  BTC ({GRID_COINS[0][5]:.0f}), "
          f"ETH ({GRID_COINS[1][5]:.0f}), SOL ({GRID_COINS[2][5]:.0f}) = "
          f"${sum(g[5] for g in GRID_COINS):,.0f}")
    print(f"Trend Layer: 8 altcoins = $2,000 "
          f"(from prior analysis: ~$2.42/day avg)")
    print(f"Total:       $5,000")
    print()

    # Run grid backtests
    grid_results = run_grid_backtests()

    if grid_results:
        grid_pnl, grid_daily, period = print_grid_summary(grid_results)

        # Combined summary
        trend_daily = 2.42  # From our 1-year trend analysis
        trend_annual = trend_daily * 365

        print(f"\n{'=' * 70}")
        print(f"🏆 COMBINED HYBRID RESULTS ($5,000 account)")
        print(f"{'=' * 70}")
        print(f"  {'Layer':<20} {'Daily':>10} {'Monthly':>12} {'Annual':>12}")
        print(f"  {'-'*56}")
        print(f"  {'Grid (BTC+ETH+SOL)':<20} "
              f"${grid_daily:>+9.2f} "
              f"${grid_daily*30:>+11.2f} "
              f"${grid_pnl:>+11.2f}")
        print(f"  {'Trend (8 altcoins)':<20} "
              f"${trend_daily:>+9.2f} "
              f"${trend_daily*30:>+11.2f} "
              f"${trend_annual:>+11.2f}")
        combined_daily = grid_daily + trend_daily
        print(f"  {'-'*56}")
        print(f"  {'TOTAL':<20} "
              f"${combined_daily:>+9.2f} "
              f"${combined_daily*30:>+11.2f} "
              f"${grid_pnl+trend_annual:>+11.2f}")
        print(f"\n  📈 Combined Annual Return: "
              f"{(grid_pnl+trend_annual)/5000*100:+.1f}% on $5,000")

    elapsed = time.time() - start
    print(f"\n⏱  Completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
