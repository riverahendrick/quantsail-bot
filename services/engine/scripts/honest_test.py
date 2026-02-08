"""Threshold test on 3-month data (which actually works).

Tests multiple confidence thresholds on proven + new symbols.
3-month × 4 = rough yearly estimate.
"""
import sys
import gc
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical" / "trimmed_3m"
CASH: float = 5000.0
DAYS: int = 90
SYMS: list[tuple[str, Path]] = [
    ("ETH", DATA_DIR / "ETH_USDT_1h_ohlcv.csv"),
    ("SOL", DATA_DIR / "SOL_USDT_1h_ohlcv.csv"),
    ("XRP", DATA_DIR / "XRP_USDT_1h_ohlcv.csv"),
    ("ADA", DATA_DIR / "ADA_USDT_1h_ohlcv.csv"),
    ("DOGE", DATA_DIR / "DOGE_USDT_1h_ohlcv.csv"),
    ("LINK", DATA_DIR / "LINK_USDT_1h_ohlcv.csv"),
    ("DOT", DATA_DIR / "DOT_USDT_1h_ohlcv.csv"),
    ("NEAR", DATA_DIR / "NEAR_USDT_1h_ohlcv.csv"),
    ("UNI", DATA_DIR / "UNI_USDT_1h_ohlcv.csv"),
    ("ARB", DATA_DIR / "ARB_USDT_1h_ohlcv.csv"),
    ("OP", DATA_DIR / "OP_USDT_1h_ohlcv.csv"),
    ("SUI", DATA_DIR / "SUI_USDT_1h_ohlcv.csv"),
    ("APT", DATA_DIR / "APT_USDT_1h_ohlcv.csv"),
]


def run(sym: str, path: Path, conf: float, wt: float) -> dict[str, Any]:
    base = BotConfig()
    t = apply_profile(base.model_dump(), "aggressive_1h")
    t["symbols"] = {"enabled": [sym]}
    t["strategies"]["ensemble"]["confidence_threshold"] = conf
    t["strategies"]["ensemble"]["weighted_threshold"] = wt
    cfg = BotConfig(**t)
    runner = BacktestRunner(
        config=cfg, data_file=path, starting_cash=CASH,
        slippage_pct=0.05, fee_pct=0.1, tick_interval_seconds=3600,
        progress_interval=99999,
    )
    m = runner.run()
    runner.close()
    r = {"trades": int(m.total_trades), "wins": int(m.winning_trades),
         "losses": int(m.losing_trades), "wr": float(m.win_rate_pct),
         "pnl": float(m.net_profit_usd)}
    del runner, m, cfg
    gc.collect()
    return r


if __name__ == "__main__":
    print("🔬 THRESHOLD SWEEP (3-month data, extrapolated to yearly)")
    print(f"   Cash: ${CASH:.0f}")
    print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")

    TESTS: list[tuple[float, float, str]] = [
        (0.40, 0.25, "Current"),
        (0.35, 0.20, "Lower"),
        (0.30, 0.15, "Medium"),
        (0.25, 0.10, "Low"),
        (0.20, 0.08, "VeryLow"),
    ]

    all_data: list[tuple[str, int, int, int, float]] = []

    for conf, wt, label in TESTS:
        print(f"\n{'='*60}")
        print(f"  {label}: conf={conf}, weighted={wt}")
        print(f"{'='*60}")
        print(f"{'Sym':6s} {'T':>3s} {'W':>3s} {'L':>3s} {'WR':>4s} {'PnL':>8s} {'$/day':>6s}")
        print("-" * 40)

        net = 0.0; tt = 0; tw = 0; tl = 0
        for sym, path in SYMS:
            if not path.exists():
                continue
            try:
                r = run(sym, path, conf, wt)
                t = r["trades"]; w = r["wins"]; lo = r["losses"]
                pnl = r["pnl"]; wr = r["wr"]; pd = pnl/DAYS
                f = "✅" if pnl > 0 else ("👁️" if t == 0 else "❌")
                print(f"{sym:6s} {t:3d} {w:3d} {lo:3d} {wr:3.0f}% ${pnl:+7.0f} ${pd:+5.2f} {f}")
                net += pnl; tt += t; tw += w; tl += lo
            except Exception as e:
                print(f"{sym:6s} ERR: {str(e)[:40]}")

        wr_a = (tw/tt*100) if tt > 0 else 0
        daily = net/DAYS
        print("-" * 40)
        print(f"TOTAL {tt:3d} {tw:3d} {tl:3d} {wr_a:3.0f}% ${net:+7.0f} ${daily:+5.2f}")
        print(f"  Yearly estimate: {tt*4} trades, ${daily*365:+.0f}/year")
        all_data.append((label, tt, tw, tl, net))

    # Summary table
    print(f"\n{'='*60}")
    print("  📊 THE HONEST TRUTH")
    print(f"{'='*60}")
    print(f"  {'Setting':10s} | {'3mo':>4s} | {'~Year':>5s} | {'WR':>4s} | {'$/day':>6s} | {'$/yr':>7s} | Verdict")
    print(f"  {'-'*10}-|-{'-'*4}-|-{'-'*5}-|-{'-'*4}-|-{'-'*6}-|-{'-'*7}-|--------")

    for label, t, w, lo, net in all_data:
        wr = (w/t*100) if t > 0 else 0
        d = net/DAYS
        yr_t = t * 4
        verdict = "✅ PROFITABLE" if net > 0 else "❌ LOSING"
        print(
            f"  {label:10s} | {t:4d} | {yr_t:5d} | {wr:3.0f}% | "
            f"${d:+5.2f} | ${d*365:+6.0f} | {verdict}"
        )

    print(f"\n⚠️  IMPORTANT CAVEATS:")
    print(f"  - These are BACKTESTS on historical data, NOT future guarantees")
    print(f"  - Past performance does NOT predict future results")
    print(f"  - Real trading has additional risks: exchange outages,")
    print(f"    API failures, slippage spikes, liquidity gaps")
    print(f"  - The strategy is PATIENT — it waits for high-conviction setups")
    print(f"  - More trades ≠ more profit (often the opposite)")

    print(f"\n  Finished: {datetime.now().strftime('%H:%M:%S')}")
