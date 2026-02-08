"""Fast profitability scanner — tests all profile × symbol combinations.

This script runs backtests faster by:
1. Increasing progress interval to avoid print overhead
2. Using in-memory DB only
3. Running all profiles × symbols sequentially
4. Outputting a clean profitability matrix
"""
import sys
import csv
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Suppress ALL logging for speed
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile, AVAILABLE_PROFILES
from quantsail_engine.backtest.runner import BacktestRunner

# Configuration
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
SYMBOLS = [
    ("BTC", "BTC_USDT_1h_ohlcv.csv"),
    ("ETH", "ETH_USDT_1h_ohlcv.csv"),
    ("SOL", "SOL_USDT_1h_ohlcv.csv"),
    ("BNB", "BNB_USDT_1h_ohlcv.csv"),
    ("XRP", "XRP_USDT_1h_ohlcv.csv"),
]
CASH = 5000.0
PROFILES = ["conservative", "moderate", "aggressive_1h"]

OUT_FILE = Path(__file__).resolve().parent / "profitability_matrix.txt"


def run_single(profile_name: str, sym: str, csv_file: str) -> dict:
    """Run a single backtest and return key metrics."""
    dp = DATA_DIR / csv_file
    if not dp.exists():
        return {"error": f"DATA NOT FOUND: {csv_file}"}

    base = BotConfig()
    tuned = apply_profile(base.model_dump(), profile_name)
    if "symbols" not in tuned:
        tuned["symbols"] = {}
    tuned["symbols"]["enabled"] = [sym]

    config = BotConfig(**tuned)

    try:
        runner = BacktestRunner(
            config=config,
            data_file=dp,
            starting_cash=CASH,
            slippage_pct=0.05,
            fee_pct=0.1,
            tick_interval_seconds=3600,
            progress_interval=99999,  # Suppress progress output
        )

        m = runner.run()
        runner.close()

        return {
            "trades": m.total_trades,
            "wins": m.winning_trades,
            "losses": m.losing_trades,
            "win_rate": m.win_rate_pct,
            "net_pnl": m.net_profit_usd,
            "end_equity": m.end_equity,
            "max_dd": m.max_drawdown_pct,
            "profitable": m.net_profit_usd > 0,
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print(f"🔍 Profitability Matrix Scanner")
    print(f"   Cash: ${CASH:.0f} | Profiles: {PROFILES}")
    print(f"   Data: {DATA_DIR}")
    print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")
    print()

    results = {}
    header = f"{'Profile':14s} {'Sym':5s} {'Trades':>6s} {'W':>3s} {'L':>3s} {'WR%':>6s} {'NetPnL':>10s} {'Equity':>10s} {'MaxDD':>7s} {'OK':>3s}"
    sep = "-" * 80
    
    print(header)
    print(sep)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n" + sep + "\n")

    for profile in PROFILES:
        for sym, csv_file in SYMBOLS:
            sys.stdout.write(f"  Running {profile}/{sym}... ")
            sys.stdout.flush()
            
            r = run_single(profile, sym, csv_file)
            
            if "error" in r:
                line = f"{profile:14s} {sym:5s}  ERROR: {r['error']}"
            else:
                ok = "✅" if r["profitable"] else "❌"
                line = (
                    f"{profile:14s} {sym:5s} {r['trades']:6d} "
                    f"{r['wins']:3d} {r['losses']:3d} "
                    f"{r['win_rate']:5.1f}% "
                    f"${r['net_pnl']:+9.2f} "
                    f"${r['end_equity']:9.2f} "
                    f"{r['max_dd']:6.2f}% {ok}"
                )
                results[(profile, sym)] = r

            print(line)
            with open(OUT_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        # Profile separator
        print(sep)
        with open(OUT_FILE, "a", encoding="utf-8") as f:
            f.write(sep + "\n")

    # Summary
    print()
    print("📊 PROFITABILITY SUMMARY")
    print("=" * 60)
    
    profitable_combos = []
    unprofitable_combos = []
    
    for (profile, sym), r in results.items():
        if "error" not in r:
            if r["profitable"]:
                profitable_combos.append((profile, sym, r))
            else:
                unprofitable_combos.append((profile, sym, r))

    if profitable_combos:
        print("\n✅ PROFITABLE (KEEP):")
        for profile, sym, r in sorted(profitable_combos, key=lambda x: -x[2]["net_pnl"]):
            print(f"   {profile}/{sym}: ${r['net_pnl']:+.2f} ({r['win_rate']:.1f}% WR, {r['max_dd']:.1f}% DD)")

    if unprofitable_combos:
        print("\n❌ UNPROFITABLE (REMOVE):")
        for profile, sym, r in sorted(unprofitable_combos, key=lambda x: x[2]["net_pnl"]):
            print(f"   {profile}/{sym}: ${r['net_pnl']:+.2f} ({r['win_rate']:.1f}% WR)")

    # Best overall
    if profitable_combos:
        best = max(profitable_combos, key=lambda x: x[2]["net_pnl"])
        print(f"\n🏆 Best combo: {best[0]}/{best[1]} = ${best[2]['net_pnl']:+.2f}")

    print(f"\n   Finished: {datetime.now().strftime('%H:%M:%S')}")
    
    # Write summary to file
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write("\n\nPROFITABLE COMBOS:\n")
        for profile, sym, r in profitable_combos:
            f.write(f"  {profile}/{sym}: ${r['net_pnl']:+.2f}\n")
        f.write("\nUNPROFITABLE COMBOS:\n")
        for profile, sym, r in unprofitable_combos:
            f.write(f"  {profile}/{sym}: ${r['net_pnl']:+.2f}\n")
