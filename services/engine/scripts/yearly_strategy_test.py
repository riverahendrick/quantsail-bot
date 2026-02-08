"""1-Year Per-Strategy Test: Find the best strategy for EACH coin.

Tests:
  Part 1: Current ensemble (aggressive_1h) × 18 symbols × 1 year
  Part 2: Each strategy ALONE × 18 symbols × 1 year (72 combos)
  Part 3: Best-strategy-per-coin summary
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
    / "data" / "historical"
)
CASH: float = 5000.0
DAYS: int = 365

# All symbols with full 1-year data
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

# Strategy weight configs for isolated testing
STRATEGY_CONFIGS: dict[str, dict[str, float]] = {
    "trend_only": {
        "weight_trend": 1.0,
        "weight_mean_reversion": 0.0,
        "weight_breakout": 0.0,
        "weight_vwap": 0.0,
    },
    "mean_rev_only": {
        "weight_trend": 0.0,
        "weight_mean_reversion": 1.0,
        "weight_breakout": 0.0,
        "weight_vwap": 0.0,
    },
    "breakout_only": {
        "weight_trend": 0.0,
        "weight_mean_reversion": 0.0,
        "weight_breakout": 1.0,
        "weight_vwap": 0.0,
    },
    "vwap_only": {
        "weight_trend": 0.0,
        "weight_mean_reversion": 0.0,
        "weight_breakout": 0.0,
        "weight_vwap": 1.0,
    },
}


def run_one(
    sym: str,
    path: Path,
    strategy_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run a single backtest. If strategy_override is None, use ensemble."""
    base = BotConfig()
    cfg_dict = apply_profile(base.model_dump(), "aggressive_1h")
    cfg_dict["symbols"] = {"enabled": [sym]}

    if strategy_override is not None:
        # Isolate single strategy
        cfg_dict["strategies"]["ensemble"]["min_agreement"] = 1
        cfg_dict["strategies"]["ensemble"]["confidence_threshold"] = 0.30
        cfg_dict["strategies"]["ensemble"]["weighted_threshold"] = 0.15
        for k, v in strategy_override.items():
            cfg_dict["strategies"]["ensemble"][k] = v

    cfg = BotConfig(**cfg_dict)
    runner = BacktestRunner(
        config=cfg,
        data_file=path,
        starting_cash=CASH,
        slippage_pct=0.05,
        fee_pct=0.1,
        tick_interval_seconds=3600,
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


def print_line(sym: str, r: dict[str, Any]) -> None:
    t = r["trades"]
    pnl = r["pnl"]
    wr = r["wr"]
    pd_val = pnl / DAYS
    yr_val = pd_val * 365
    flag = "✅" if pnl > 0 else ("👁️" if t == 0 else "❌")
    print(f"{sym:5s} {t:3d} {r['wins']:3d} {r['losses']:3d} "
          f"{wr:3.0f}% ${pnl:+8.0f} ${pd_val:+5.2f} ${yr_val:+7.0f} {flag}")


if __name__ == "__main__":
    print("=" * 80)
    print("  🔬 1-YEAR PER-STRATEGY TEST: Find Best Strategy For Each Coin")
    print(f"  Cash: ${CASH:.0f} | Period: 1 year (365 days) | 18 symbols")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)

    # ──────────────────────────────────────────────
    # PART 1: Current ensemble on full year
    # ──────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  PART 1: Current Ensemble (aggressive_1h) — Full Year")
    print(f"{'─' * 70}")
    print(f"{'Sym':5s} {'T':>3s} {'W':>3s} {'L':>3s} {'WR':>4s} "
          f"{'PnL':>8s} {'$/day':>6s} {'$/year':>8s}")
    print("-" * 55)

    ensemble_results: dict[str, dict[str, Any]] = {}
    for sym, path in SYMBOLS:
        if not path.exists():
            print(f"{sym:5s} SKIP (no data)")
            continue
        try:
            r = run_one(sym, path, strategy_override=None)
            ensemble_results[sym] = r
            print_line(sym, r)
        except Exception as e:
            print(f"{sym:5s} ERR: {str(e)[:50]}")

    # Ensemble totals
    e_tot_t = sum(r["trades"] for r in ensemble_results.values())
    e_tot_w = sum(r["wins"] for r in ensemble_results.values())
    e_tot_pnl = sum(r["pnl"] for r in ensemble_results.values())
    e_wr = (e_tot_w / e_tot_t * 100) if e_tot_t > 0 else 0
    e_daily = e_tot_pnl / DAYS
    print("-" * 55)
    print(f"TOTAL {e_tot_t:3d} {e_tot_w:3d} {e_tot_t-e_tot_w:3d} "
          f"{e_wr:3.0f}% ${e_tot_pnl:+8.0f} ${e_daily:+5.2f} "
          f"${e_daily*365:+7.0f}")

    # ──────────────────────────────────────────────
    # PART 2: Each strategy individually
    # ──────────────────────────────────────────────
    # Store: {symbol: {strategy_name: result}}
    strategy_matrix: dict[str, dict[str, dict[str, Any]]] = {}

    for strat_name, weights in STRATEGY_CONFIGS.items():
        print(f"\n{'─' * 70}")
        print(f"  PART 2: {strat_name.upper()} — Full Year")
        print(f"{'─' * 70}")
        print(f"{'Sym':5s} {'T':>3s} {'W':>3s} {'L':>3s} {'WR':>4s} "
              f"{'PnL':>8s} {'$/day':>6s} {'$/year':>8s}")
        print("-" * 55)

        for sym, path in SYMBOLS:
            if not path.exists():
                continue
            try:
                r = run_one(sym, path, strategy_override=weights)
                if sym not in strategy_matrix:
                    strategy_matrix[sym] = {}
                strategy_matrix[sym][strat_name] = r
                print_line(sym, r)
            except Exception as e:
                print(f"{sym:5s} ERR: {str(e)[:50]}")

    # ──────────────────────────────────────────────
    # PART 3: Best strategy per coin
    # ──────────────────────────────────────────────
    print(f"\n\n{'=' * 80}")
    print("  🏆 BEST STRATEGY PER COIN (1-Year Data)")
    print(f"{'=' * 80}")
    print(f"{'Sym':5s} {'Best Strategy':15s} {'vs Ensemble':12s} "
          f"{'T':>3s} {'WR':>4s} {'PnL/yr':>8s} {'$/day':>7s} {'Status'}")
    print("-" * 75)

    profitable_coins: list[tuple[str, str, dict[str, Any]]] = []
    all_strategies = list(STRATEGY_CONFIGS.keys()) + ["ensemble"]

    for sym, _ in SYMBOLS:
        # Collect all results for this symbol
        all_results: dict[str, dict[str, Any]] = {}
        if sym in strategy_matrix:
            all_results.update(strategy_matrix[sym])
        if sym in ensemble_results:
            all_results["ensemble"] = ensemble_results[sym]

        if not all_results:
            continue

        # Find best by PnL
        best_strat = ""
        best_r: dict[str, Any] = {"pnl": -99999, "trades": 0, "wr": 0}
        for sname, sresult in all_results.items():
            if sresult["pnl"] > best_r["pnl"]:
                best_r = sresult
                best_strat = sname

        pnl = best_r["pnl"]
        t = best_r["trades"]
        wr = best_r["wr"]
        pd_val = pnl / DAYS

        # Compare to ensemble
        e_pnl = ensemble_results.get(sym, {}).get("pnl", 0)
        diff = pnl - e_pnl
        comp = f"${diff:+.0f}" if abs(diff) > 0.5 else "same"

        if t == 0:
            status = "👁️ WATCH"
        elif pnl > 0:
            profitable_coins.append((sym, best_strat, best_r))
            status = "✅ TRADE"
        else:
            status = "❌ CUT"

        print(f"{sym:5s} {best_strat:15s} {comp:12s} {t:3d} {wr:3.0f}% "
              f"${pnl:+8.0f} ${pd_val:+6.2f}  {status}")

    # ──────────────────────────────────────────────
    # FINAL SUMMARY
    # ──────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("  📊 RECOMMENDED PRODUCTION CONFIG")
    print(f"{'=' * 80}")

    if profitable_coins:
        total_daily = 0.0
        total_trades = 0
        print("\n  Per-coin routing:")
        for sym, strat, res in profitable_coins:
            pd_val = res["pnl"] / DAYS
            total_daily += pd_val
            total_trades += res["trades"]
            print(f"    {sym:5s} → {strat:15s} "
                  f"({res['trades']}t, WR {res['wr']:.0f}%, "
                  f"${pd_val:+.2f}/day)")
        print(f"\n    Combined: {total_trades} trades/year, "
              f"${total_daily:+.2f}/day, ${total_daily*365:+.0f}/year")

    # Full strategy matrix
    print(f"\n{'=' * 80}")
    print("  📋 FULL STRATEGY MATRIX (PnL per year)")
    print(f"{'=' * 80}")
    header = f"{'Sym':5s} | {'ensemble':>10s}"
    for s in STRATEGY_CONFIGS:
        header += f" | {s:>12s}"
    print(header)
    print("-" * len(header))

    for sym, _ in SYMBOLS:
        line = f"{sym:5s} |"
        # Ensemble
        e_pnl = ensemble_results.get(sym, {}).get("pnl", 0)
        line += f" ${e_pnl:+9.0f}"
        # Individual strategies
        for s in STRATEGY_CONFIGS:
            s_pnl = strategy_matrix.get(sym, {}).get(s, {}).get("pnl", 0)
            line += f" | ${s_pnl:+11.0f}"
        print(line)

    print(f"\n  Finished: {datetime.now().strftime('%H:%M:%S')}")
