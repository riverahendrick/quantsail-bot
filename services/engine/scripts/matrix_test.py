"""Matrix test: ALL profiles × ALL symbols (1h data).

Tests 5 profiles × 16 symbols = 80 combinations on 3-month trimmed data.
Finds the BEST profile for each symbol and builds the optimal config map.
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

DATA_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "historical" / "trimmed_3m"
)
CASH: float = 5000.0
DAYS: int = 90

# All 1h-compatible profiles
PROFILES: list[str] = [
    "conservative",
    "moderate",
    "aggressive",
    "aggressive_1h",
    "daily_target",
]

# All symbols with trimmed 1h data
SYMBOLS: list[tuple[str, Path]] = [
    ("BTC", DATA_DIR / "BTC_USDT_1h_ohlcv.csv"),
    ("ETH", DATA_DIR / "ETH_USDT_1h_ohlcv.csv"),
    ("BNB", DATA_DIR / "BNB_USDT_1h_ohlcv.csv"),
    ("SOL", DATA_DIR / "SOL_USDT_1h_ohlcv.csv"),
    ("XRP", DATA_DIR / "XRP_USDT_1h_ohlcv.csv"),
    ("ADA", DATA_DIR / "ADA_USDT_1h_ohlcv.csv"),
    ("DOGE", DATA_DIR / "DOGE_USDT_1h_ohlcv.csv"),
    ("LINK", DATA_DIR / "LINK_USDT_1h_ohlcv.csv"),
    ("DOT", DATA_DIR / "DOT_USDT_1h_ohlcv.csv"),
    ("AVAX", DATA_DIR / "AVAX_USDT_1h_ohlcv.csv"),
    ("ATOM", DATA_DIR / "ATOM_USDT_1h_ohlcv.csv"),
    ("POL", DATA_DIR / "POL_USDT_1h_ohlcv.csv"),
    ("NEAR", DATA_DIR / "NEAR_USDT_1h_ohlcv.csv"),
    ("UNI", DATA_DIR / "UNI_USDT_1h_ohlcv.csv"),
    ("ARB", DATA_DIR / "ARB_USDT_1h_ohlcv.csv"),
    ("OP", DATA_DIR / "OP_USDT_1h_ohlcv.csv"),
    ("SUI", DATA_DIR / "SUI_USDT_1h_ohlcv.csv"),
    ("APT", DATA_DIR / "APT_USDT_1h_ohlcv.csv"),
]


def run_one(sym: str, path: Path, profile: str) -> dict[str, Any]:
    """Run a single backtest for one symbol + profile combo."""
    base = BotConfig()
    cfg_dict = apply_profile(base.model_dump(), profile)
    cfg_dict["symbols"] = {"enabled": [sym]}
    cfg = BotConfig(**cfg_dict)
    runner = BacktestRunner(
        config=cfg, data_file=path, starting_cash=CASH,
        slippage_pct=0.05, fee_pct=0.1, tick_interval_seconds=3600,
        progress_interval=99999,
    )
    m = runner.run()
    runner.close()
    result: dict[str, Any] = {
        "trades": int(m.total_trades),
        "wins": int(m.winning_trades),
        "losses": int(m.losing_trades),
        "wr": float(m.win_rate_pct),
        "pnl": float(m.net_profit_usd),
    }
    del runner, m, cfg
    gc.collect()
    return result


if __name__ == "__main__":
    print("=" * 80)
    print("  🔬 FULL MATRIX TEST: 5 Profiles × 18 Symbols")
    print(f"  Cash: ${CASH:.0f} | Period: 3 months (90 days)")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)

    # Results: {symbol: {profile: result_dict}}
    matrix: dict[str, dict[str, dict[str, Any]]] = {}

    for profile in PROFILES:
        print(f"\n{'─' * 70}")
        print(f"  Profile: {profile}")
        print(f"{'─' * 70}")
        print(f"{'Sym':5s} {'T':>3s} {'W':>3s} {'L':>3s} {'WR':>4s} "
              f"{'PnL':>8s} {'$/day':>6s}")
        print("-" * 40)

        for sym, path in SYMBOLS:
            if not path.exists():
                print(f"{sym:5s} SKIP (no data)")
                continue
            try:
                r = run_one(sym, path, profile)
                t = r["trades"]
                pnl = r["pnl"]
                wr = r["wr"]
                pd_val = pnl / DAYS
                flag = "✅" if pnl > 0 else ("👁️" if t == 0 else "❌")
                print(f"{sym:5s} {t:3d} {r['wins']:3d} {r['losses']:3d} "
                      f"{wr:3.0f}% ${pnl:+7.0f} ${pd_val:+5.2f} {flag}")

                # Store in matrix
                if sym not in matrix:
                    matrix[sym] = {}
                matrix[sym][profile] = r
            except Exception as e:
                print(f"{sym:5s} ERR: {str(e)[:50]}")

    # ========================================================
    # BEST PROFILE PER SYMBOL
    # ========================================================
    print(f"\n\n{'=' * 80}")
    print("  📊 BEST PROFILE PER SYMBOL (Ranked by PnL)")
    print(f"{'=' * 80}")
    print(f"{'Sym':5s} {'Best Profile':20s} {'T':>3s} {'WR':>4s} "
          f"{'PnL/3mo':>8s} {'$/day':>7s} {'$/year':>8s} {'Status'}")
    print("-" * 75)

    profitable: list[tuple[str, str, dict[str, Any]]] = []
    watching: list[str] = []
    losers: list[tuple[str, str, float]] = []

    for sym, profiles_data in matrix.items():
        # Find best profile by PnL
        best_profile = ""
        best_result: dict[str, Any] = {"pnl": -99999}
        for prof, res in profiles_data.items():
            if res["pnl"] > best_result["pnl"]:
                best_result = res
                best_profile = prof

        pnl = best_result["pnl"]
        t = best_result["trades"]
        wr = best_result["wr"]
        pd_val = pnl / DAYS
        yr_val = pd_val * 365

        if t == 0:
            watching.append(sym)
            status = "👁️ WATCH"
        elif pnl > 0:
            profitable.append((sym, best_profile, best_result))
            status = "✅ TRADE"
        else:
            losers.append((sym, best_profile, pnl))
            status = "❌ CUT"

        print(f"{sym:5s} {best_profile:20s} {t:3d} {wr:3.0f}% "
              f"${pnl:+7.0f} ${pd_val:+6.2f} ${yr_val:+7.0f}  {status}")

    # ========================================================
    # SUMMARY
    # ========================================================
    print(f"\n{'=' * 80}")
    print("  🏆 FINAL RECOMMENDED CONFIGURATION")
    print(f"{'=' * 80}")

    if profitable:
        print("\n  ✅ ACTIVELY TRADE (with their best profile):")
        total_daily = 0.0
        total_trades = 0
        for sym, prof, res in profitable:
            pd_val = res["pnl"] / DAYS
            total_daily += pd_val
            total_trades += res["trades"]
            print(f"    {sym:5s} → {prof:20s} ({res['trades']} trades, "
                  f"WR {res['wr']:.0f}%, ${pd_val:+.2f}/day)")
        print(f"\n    Combined: {total_trades} trades/3mo, "
              f"${total_daily:+.2f}/day, ${total_daily*365:+.0f}/year")

    if watching:
        print(f"\n  👁️ WATCH ONLY (no signals from any profile): "
              f"{', '.join(watching)}")

    if losers:
        print(f"\n  ❌ CUT (best profile still loses):")
        for sym, prof, pnl in losers:
            print(f"    {sym:5s} → best was {prof:20s} (still ${pnl:+.0f})")

    print(f"\n  Finished: {datetime.now().strftime('%H:%M:%S')}")
