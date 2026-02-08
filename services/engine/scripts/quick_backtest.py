"""Quick backtest summary — writes results to file and saves detailed CSVs."""
import sys
import csv
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
# We typically run this from services/engine/, so adding parent of parent
sys.path.append(str(Path(__file__).resolve().parents[1]))

logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

# Match the data directory structure
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
# BTC removed — consistently unprofitable on all strategies (1-year backtest)
# Per-coin routing: each coin uses its best strategy via production_routing profile
SYMBOLS = [
    ("ETH",  "ETH_USDT_1h_ohlcv.csv"),    # ensemble
    ("SOL",  "SOL_USDT_1h_ohlcv.csv"),     # ensemble
    ("XRP",  "XRP_USDT_1h_ohlcv.csv"),     # trend_only
    ("AVAX", "AVAX_USDT_1h_ohlcv.csv"),    # trend_only
    ("NEAR", "NEAR_USDT_1h_ohlcv.csv"),    # trend_only
    ("APT",  "APT_USDT_1h_ohlcv.csv"),     # trend_only
    ("ATOM", "ATOM_USDT_1h_ohlcv.csv"),    # trend_only
    ("POL",  "POL_USDT_1h_ohlcv.csv"),     # trend_only
    ("SUI",  "SUI_USDT_1h_ohlcv.csv"),     # trend_only
    ("DOGE", "DOGE_USDT_1h_ohlcv.csv"),    # mean_rev_only
    ("BNB",  "BNB_USDT_1h_ohlcv.csv"),     # vwap_only
]

# Use the new per-coin routing profile
PROFILES = ["production_routing"]
CASH = 5000.0
OUT_FILE = Path(__file__).resolve().parent / "backtest_results.txt"


def save_detailed_reports(metrics, profile, symbol):
    """Save detailed trade log and daily PnL to CSV."""
    # 1. Trades CSV
    trades_file = Path(__file__).parent / f"trades_{profile}_{symbol}.csv"
    with open(trades_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "entry_time", "exit_time", "symbol", "side", 
            "entry_price", "exit_price", "quantity", 
            "pnl_usd", "pnl_pct", "exit_reason", "status"
        ])
        for t in metrics.trades:
            writer.writerow([
                t.get("id"),
                t.get("opened_at"),  # Entry time
                t.get("closed_at"),
                t.get("symbol"),
                t.get("side"),
                t.get("entry_price"),
                t.get("exit_price"),
                t.get("quantity"),
                t.get("realized_pnl_usd"),
                t.get("pnl_pct"),
                t.get("exit_reason"),
                t.get("status")
            ])

    # 2. Daily PnL CSV
    daily_pnl = {}
    for t in metrics.trades:
        # Only closed trades contribute to realized PnL for this report
        if t.get("status") == "CLOSED" and t.get("closed_at"):
            dt = t.get("closed_at")
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt)
                except ValueError:
                    continue
            date_str = dt.strftime("%Y-%m-%d")
            daily_pnl[date_str] = daily_pnl.get(date_str, 0.0) + (t.get("realized_pnl_usd") or 0.0)

    daily_file = Path(__file__).parent / f"daily_{profile}_{symbol}.csv"
    with open(daily_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "pnl_usd"])
        for date, pnl in sorted(daily_pnl.items()):
            writer.writerow([date, f"{pnl:.2f}"])

    print(f"   Saved details: {trades_file.name}, {daily_file.name}")


if __name__ == "__main__":
    print(f"Starting Quick Backtest (Stream Output)...")
    print(f"Output File: {OUT_FILE}")
    
    # Initialize output file with header
    header = (
        f"{'Profile':14s} {'Sym':6s} {'Trades':>6s} "
        f"{'Win':>4s} {'Loss':>4s} {'Win%':>6s} "
        f"{'NetPnL':>10s} {'EndEquity':>12s} {'MaxDD':>7s}"
    )
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n" + ("-" * 80) + "\n")
    print(header)
    print("-" * 80)

    for profile in PROFILES:
        for sym, csv_file in SYMBOLS:
            dp = DATA_DIR / csv_file
            if not dp.exists():
                msg = f"{profile:14s} {sym:6s}  DATA NOT FOUND: {csv_file}"
                print(msg)
                continue
            
            print(f"\n--- Testing Profile: {profile} | Symbol: {sym} ---")
            
            base = BotConfig()
            tuned = apply_profile(base.model_dump(), profile)
            # Ensure symbol enablement for the config
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
                    tick_interval_seconds=3600,  # 1h interval matches data
                    progress_interval=500  # Less frequent progress updates
                )
                
                m = runner.run()
                
                line = (
                    f"{profile:14s} {sym:6s} {m.total_trades:6d} "
                    f"{m.winning_trades:4d} {m.losing_trades:4d} "
                    f"{m.win_rate_pct:5.1f}% "
                    f"${m.net_profit_usd:+9.2f} "
                    f"${m.end_equity:11.2f} "
                    f"{m.max_drawdown_pct:6.2f}%"
                )
                print(line)
                with open(OUT_FILE, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                
                # Save detailed reports
                save_detailed_reports(m, profile, sym)
                    
                runner.close()
                
            except Exception as e:
                msg = f"{profile:14s} {sym:6s}  ERROR: {e}"
                print(msg)
                # print stack trace for debugging if needed
                import traceback
                traceback.print_exc()
                with open(OUT_FILE, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")

    print("-" * 80)
    print("Done.")
