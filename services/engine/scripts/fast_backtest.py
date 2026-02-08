"""Fast 3-month backtest using trimmed CSV files.

Uses trimmed data (2,162 candles = ~3 months) for fast profitability validation.
Tests daily_target and aggressive_1h on profitable symbols only.
"""
import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical" / "trimmed_3m"

# Only profitable symbols (BTC and BNB removed)
SYMBOLS = [
    ("ETH", "ETH_USDT_1h_ohlcv.csv"),
    ("SOL", "SOL_USDT_1h_ohlcv.csv"),
    ("XRP", "XRP_USDT_1h_ohlcv.csv"),
]

PROFILES = ["aggressive_1h", "daily_target"]
CASH = 5000.0


def run_backtest(profile: str, sym: str, csv_file: str):
    """Run a single backtest and return metrics dict."""
    dp = DATA_DIR / csv_file

    base = BotConfig()
    tuned = apply_profile(base.model_dump(), profile)
    tuned.setdefault("symbols", {})
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
            progress_interval=99999,
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
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    print("🚀 Fast 3-Month Backtest (Trimmed Data)")
    print(f"   Cash: ${CASH:.0f} | Period: Nov 2025 - Feb 2026")
    print()

    header = f"{'Profile':14s} {'Sym':5s} {'Trades':>6s} {'W':>3s} {'L':>3s} {'WR%':>6s} {'NetPnL':>10s} {'$/day':>8s} {'DD%':>6s} {'OK':>3s}"
    print(header)
    print("-" * 78)

    all_results = []

    for profile in PROFILES:
        for sym, csv_file in SYMBOLS:
            r = run_backtest(profile, sym, csv_file)
            if "error" in r:
                print(f"{profile:14s} {sym:5s}  ERROR: {r['error']}")
                continue

            pnl: float = float(r["net_pnl"])
            pnl_day: float = pnl / 90.0
            ok = "✅" if pnl > 0 else "❌"
            line = (
                f"{profile:14s} {sym:5s} {r['trades']:6d} "
                f"{r['wins']:3d} {r['losses']:3d} "
                f"{r['win_rate']:5.1f}% "
                f"${pnl:+9.2f} "
                f"${pnl_day:+7.2f} "
                f"{r['max_dd']:5.1f}% {ok}"
            )
            print(line)
            r["profile"] = profile  # type: ignore[assignment]
            r["symbol"] = sym  # type: ignore[assignment]
            r["pnl_day"] = pnl_day  # type: ignore[assignment]
            all_results.append(r)

        print("-" * 78)

    # Summary
    print()
    profitable = [r for r in all_results if r.get("net_pnl", 0) > 0]
    unprofitable = [r for r in all_results if r.get("net_pnl", 0) <= 0]

    if profitable:
        print("✅ PROFITABLE:")
        for r in sorted(profitable, key=lambda x: -x["pnl_day"]):
            print(f"   {r['profile']}/{r['symbol']}: ${r['pnl_day']:+.2f}/day ({r['win_rate']:.0f}% WR, {r['max_dd']:.1f}% DD)")
        total_daily = sum(r["pnl_day"] for r in profitable)
        # Only count best profile per symbol to avoid double-counting
        best_by_sym = {}
        for r in profitable:
            if r["symbol"] not in best_by_sym or r["pnl_day"] > best_by_sym[r["symbol"]]["pnl_day"]:
                best_by_sym[r["symbol"]] = r
        best_daily = sum(r["pnl_day"] for r in best_by_sym.values())
        print(f"\n   💰 Best per-symbol daily: ${best_daily:.2f}/day")

    if unprofitable:
        print(f"\n❌ UNPROFITABLE:")
        for r in sorted(unprofitable, key=lambda x: x.get("net_pnl", 0)):
            print(f"   {r['profile']}/{r['symbol']}: ${r.get('pnl_day', 0):+.2f}/day")
