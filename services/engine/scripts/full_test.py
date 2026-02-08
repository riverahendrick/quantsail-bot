"""Comprehensive backtest: test ALL symbols on 1h and sample 5m.

Tests:
  - New 1h symbols: ADA, DOGE, AVAX, LINK, DOT (8,760 candles = 1 year)
  - Existing profitable 1h: ETH, SOL, XRP (trimmed 3-month data)
  - 5m data: ETH, SOL, XRP, ADA (25,920 candles = 90 days)
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
TRIMMED_DIR = DATA_DIR / "trimmed_3m"
CASH = 5000.0


def run(profile: str, sym: str, csv_path: Path, tick_secs: int) -> dict:
    """Run a single backtest."""
    base = BotConfig()
    tuned = apply_profile(base.model_dump(), profile)
    tuned.setdefault("symbols", {})
    tuned["symbols"]["enabled"] = [sym]
    config = BotConfig(**tuned)

    try:
        runner = BacktestRunner(
            config=config, data_file=csv_path, starting_cash=CASH,
            slippage_pct=0.05, fee_pct=0.1, tick_interval_seconds=tick_secs,
            progress_interval=99999,
        )
        m = runner.run()
        runner.close()
        return {
            "trades": m.total_trades, "wins": m.winning_trades,
            "losses": m.losing_trades, "wr": m.win_rate_pct,
            "pnl": m.net_profit_usd, "dd": m.max_drawdown_pct,
        }
    except Exception as e:
        return {"error": str(e)}


def test_batch(label: str, tests: list, profile: str, tick_secs: int):
    """Run a batch of tests and print results."""
    print(f"\n{'='*70}")
    print(f"  {label}  |  Profile: {profile}  |  Tick: {tick_secs}s")
    print(f"{'='*70}")
    header = f"{'Sym':6s} {'Trades':>6s} {'W':>3s} {'L':>3s} {'WR%':>6s} {'NetPnL':>10s} {'$/day':>8s} {'DD%':>6s} {'OK':>3s}"
    print(header)
    print("-" * 60)

    results = []
    for sym, csv_path, days in tests:
        if not csv_path.exists():
            print(f"{sym:6s} MISSING: {csv_path.name}")
            continue
        r = run(profile, sym, csv_path, tick_secs)
        if "error" in r:
            print(f"{sym:6s} ERROR: {r['error'][:50]}")
            continue

        pnl_day = r["pnl"] / days
        ok = "✅" if r["pnl"] > 0 else ("⚪" if r["trades"] == 0 else "❌")
        print(
            f"{sym:6s} {r['trades']:6d} {r['wins']:3d} {r['losses']:3d} "
            f"{r['wr']:5.1f}% ${r['pnl']:+9.2f} ${pnl_day:+7.2f} "
            f"{r['dd']:5.1f}% {ok}"
        )
        r.update({"sym": sym, "pnl_day": pnl_day, "days": days})
        results.append(r)
    return results


if __name__ == "__main__":
    print(f"🔬 Comprehensive Symbol & Timeframe Test")
    print(f"   Cash: ${CASH:.0f}")
    print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")

    all_results = []

    # === TEST 1: New 1h symbols (full year — but slow, so use trimmed 3m) ===
    # First, create trimmed 3m versions of new symbols
    TRIMMED_DIR.mkdir(parents=True, exist_ok=True)
    for sym in ["ADA", "DOGE", "AVAX", "LINK", "DOT"]:
        src = DATA_DIR / f"{sym}_USDT_1h_ohlcv.csv"
        dst = TRIMMED_DIR / f"{sym}_USDT_1h_ohlcv.csv"
        if src.exists() and not dst.exists():
            import csv as csvmod
            with open(src, 'r') as f:
                reader = csvmod.reader(f)
                header = next(reader)
                rows = list(reader)
            # Last 2162 rows (~3 months)
            trimmed = rows[-2162:]
            with open(dst, 'w', newline='') as f:
                writer = csvmod.writer(f)
                writer.writerow(header)
                writer.writerows(trimmed)
            print(f"📋 Trimmed {sym}: {len(rows)} → {len(trimmed)} rows")

    new_1h = [
        ("ADA", TRIMMED_DIR / "ADA_USDT_1h_ohlcv.csv", 90),
        ("DOGE", TRIMMED_DIR / "DOGE_USDT_1h_ohlcv.csv", 90),
        ("AVAX", TRIMMED_DIR / "AVAX_USDT_1h_ohlcv.csv", 90),
        ("LINK", TRIMMED_DIR / "LINK_USDT_1h_ohlcv.csv", 90),
        ("DOT", TRIMMED_DIR / "DOT_USDT_1h_ohlcv.csv", 90),
    ]
    all_results += test_batch("NEW COINS — 1h (3-month)", new_1h, "aggressive_1h", 3600)

    # === TEST 2: Proven 1h symbols (confirm still working) ===
    proven_1h = [
        ("ETH", TRIMMED_DIR / "ETH_USDT_1h_ohlcv.csv", 90),
        ("SOL", TRIMMED_DIR / "SOL_USDT_1h_ohlcv.csv", 90),
        ("XRP", TRIMMED_DIR / "XRP_USDT_1h_ohlcv.csv", 90),
    ]
    all_results += test_batch("PROVEN WINNERS — 1h (confirm)", proven_1h, "aggressive_1h", 3600)

    # === TEST 3: 5m data for best symbols ===
    test_5m = [
        ("ETH", DATA_DIR / "ETH_USDT_5m_ohlcv.csv", 90),
        ("SOL", DATA_DIR / "SOL_USDT_5m_ohlcv.csv", 90),
        ("XRP", DATA_DIR / "XRP_USDT_5m_ohlcv.csv", 90),
        ("ADA", DATA_DIR / "ADA_USDT_5m_ohlcv.csv", 90),
    ]
    all_results += test_batch("5-MINUTE DATA (90 days)", test_5m, "aggressive_5m", 300)

    # === SUMMARY ===
    print(f"\n{'='*70}")
    print("  FINAL SUMMARY")
    print(f"{'='*70}")

    profitable = [r for r in all_results if r.get("pnl", 0) > 0]
    unprofitable = [r for r in all_results if r.get("pnl", 0) <= 0 and r.get("trades", 0) > 0]
    no_trades = [r for r in all_results if r.get("trades", 0) == 0]

    if profitable:
        print("\n✅ PROFITABLE (keep these):")
        for r in sorted(profitable, key=lambda x: -x["pnl_day"]):
            print(f"   {r['sym']:6s} ${r['pnl_day']:+.2f}/day  ({r['wr']:.0f}% WR, {r['dd']:.1f}% DD)")
        total = sum(r["pnl_day"] for r in profitable)
        print(f"\n   💰 Combined: ${total:.2f}/day = ${total*30:.0f}/month = ${total*365:.0f}/year")

    if unprofitable:
        print("\n❌ UNPROFITABLE (remove):")
        for r in sorted(unprofitable, key=lambda x: x.get("pnl", 0)):
            print(f"   {r['sym']:6s} ${r.get('pnl_day',0):+.2f}/day  ({r['wr']:.0f}% WR)")

    if no_trades:
        print("\n⚪ NO TRADES (profile too strict):")
        for r in no_trades:
            print(f"   {r['sym']:6s}")

    print(f"\n   Finished: {datetime.now().strftime('%H:%M:%S')}")
