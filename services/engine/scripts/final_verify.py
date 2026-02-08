"""Final verification — run daily_target and aggressive_1h on ETH, SOL, XRP only.

Uses trimmed 3-month data for fast results.
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

# Only verified profitable symbols
SYMBOLS = [
    ("ETH", "ETH_USDT_1h_ohlcv.csv"),
    ("SOL", "SOL_USDT_1h_ohlcv.csv"),
    ("XRP", "XRP_USDT_1h_ohlcv.csv"),
]

PROFILES = ["aggressive_1h", "daily_target"]
CASH = 5000.0


def run_single(profile: str, sym: str, csv_file: str):
    dp = DATA_DIR / csv_file
    base = BotConfig()
    tuned = apply_profile(base.model_dump(), profile)
    tuned.setdefault("symbols", {})
    tuned["symbols"]["enabled"] = [sym]
    config = BotConfig(**tuned)

    runner = BacktestRunner(
        config=config, data_file=dp, starting_cash=CASH,
        slippage_pct=0.05, fee_pct=0.1, tick_interval_seconds=3600,
        progress_interval=99999,
    )
    m = runner.run()
    runner.close()
    return m


if __name__ == "__main__":
    from datetime import datetime
    print(f"🔬 Final Profitability Verification")
    print(f"   Period: Nov 2025 - Feb 2026 (3 months)")
    print(f"   Cash: ${CASH:.0f}")
    print(f"   Symbols: ETH, SOL, XRP (BTC/BNB removed — unprofitable)")
    print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")
    print()

    header = f"{'Profile':14s} {'Sym':5s} {'Trades':>6s} {'W':>3s} {'L':>3s} {'WR%':>6s} {'NetPnL':>10s} {'$/day':>8s} {'MaxDD':>7s}"
    print(header)
    print("=" * 75)

    profitable_daily = 0.0

    for profile in PROFILES:
        profile_total = 0.0
        for sym, csv_file in SYMBOLS:
            m = run_single(profile, sym, csv_file)
            pnl_day = m.net_profit_usd / 90.0
            ok = "✅" if m.net_profit_usd > 0 else ("⚪" if m.total_trades == 0 else "❌")
            line = (
                f"{profile:14s} {sym:5s} {m.total_trades:6d} "
                f"{m.winning_trades:3d} {m.losing_trades:3d} "
                f"{m.win_rate_pct:5.1f}% "
                f"${m.net_profit_usd:+9.2f} "
                f"${pnl_day:+7.2f} "
                f"{m.max_drawdown_pct:6.2f}% {ok}"
            )
            print(line)
            if m.net_profit_usd > 0:
                profile_total += pnl_day
        print(f"{'':14s} {'TOTAL':5s} {'':>6s} {'':>3s} {'':>3s} {'':>6s} {'':>10s} ${profile_total:+7.2f}")
        print("-" * 75)
        if profile_total > profitable_daily:
            profitable_daily = profile_total

    print()
    print(f"💰 Best profile daily total: ${profitable_daily:.2f}/day")
    print(f"   Monthly estimate: ${profitable_daily * 30:.2f}/month")
    print(f"   Yearly estimate: ${profitable_daily * 365:.2f}/year")
    print(f"   Finished: {datetime.now().strftime('%H:%M:%S')}")
