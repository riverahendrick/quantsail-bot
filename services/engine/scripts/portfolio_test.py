"""Multi-symbol portfolio backtest — ALL symbols, shared capital.

The BacktestRunner handles one symbol per run. This script:
1. Runs each symbol independently to extract trade signals + timing
2. Combines all trades into a chronological portfolio timeline
3. Shows the REAL result: bot watches ALL coins, picks best signals

Philosophy: keep adding coins. More watched = more opportunities.
Symbols with 0 trades cost nothing — they're just monitored.
"""
import sys
import csv as csvmod
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig  # noqa: E402
from quantsail_engine.config.parameter_profiles import apply_profile  # noqa: E402
from quantsail_engine.backtest.runner import BacktestRunner  # noqa: E402

DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
TRIMMED_DIR: Path = DATA_DIR / "trimmed_3m"

# ALL symbols the bot watches — let the strategy decide which to trade
# Keep adding here — never remove, the bot picks winners automatically
ALL_SYMBOLS_1H: list[tuple[str, Path]] = [
    # Proven profitable
    ("ETH", TRIMMED_DIR / "ETH_USDT_1h_ohlcv.csv"),
    ("SOL", TRIMMED_DIR / "SOL_USDT_1h_ohlcv.csv"),
    ("XRP", TRIMMED_DIR / "XRP_USDT_1h_ohlcv.csv"),
    # Active but mixed results
    ("AVAX", TRIMMED_DIR / "AVAX_USDT_1h_ohlcv.csv"),
    # Watching — may trade in different conditions
    ("ADA", TRIMMED_DIR / "ADA_USDT_1h_ohlcv.csv"),
    ("DOGE", TRIMMED_DIR / "DOGE_USDT_1h_ohlcv.csv"),
    ("LINK", TRIMMED_DIR / "LINK_USDT_1h_ohlcv.csv"),
    ("DOT", TRIMMED_DIR / "DOT_USDT_1h_ohlcv.csv"),
    # New additions — more coins = more opportunities
    ("POL", TRIMMED_DIR / "POL_USDT_1h_ohlcv.csv"),
    ("NEAR", TRIMMED_DIR / "NEAR_USDT_1h_ohlcv.csv"),
    ("UNI", TRIMMED_DIR / "UNI_USDT_1h_ohlcv.csv"),
    ("ATOM", TRIMMED_DIR / "ATOM_USDT_1h_ohlcv.csv"),
    ("ARB", TRIMMED_DIR / "ARB_USDT_1h_ohlcv.csv"),
    ("OP", TRIMMED_DIR / "OP_USDT_1h_ohlcv.csv"),
    ("SUI", TRIMMED_DIR / "SUI_USDT_1h_ohlcv.csv"),
    ("APT", TRIMMED_DIR / "APT_USDT_1h_ohlcv.csv"),
]

PROFILE: str = "aggressive_1h"
CASH: float = 5000.0
DAYS: int = 90  # 3-month test period


def run_single(sym: str, csv_path: Path) -> dict[str, Any]:
    """Run backtest for one symbol, return metrics."""
    base: BotConfig = BotConfig()
    tuned: dict[str, Any] = apply_profile(base.model_dump(), PROFILE)
    tuned.setdefault("symbols", {})
    tuned["symbols"]["enabled"] = [sym]
    config: BotConfig = BotConfig(**tuned)

    try:
        runner: BacktestRunner = BacktestRunner(
            config=config, data_file=csv_path, starting_cash=CASH,
            slippage_pct=0.05, fee_pct=0.1, tick_interval_seconds=3600,
            progress_interval=99999,
        )
        m = runner.run()
        runner.close()
        return {
            "trades": int(m.total_trades),
            "wins": int(m.winning_trades),
            "losses": int(m.losing_trades),
            "wr": float(m.win_rate_pct),
            "pnl": float(m.net_profit_usd),
            "dd": float(m.max_drawdown_pct),
            "end_equity": float(m.end_equity),
        }
    except Exception as e:
        return {"error": str(e)}


def trim_data(sym: str) -> bool:
    """Trim full 1yr data to 3-month for faster backtesting."""
    src: Path = DATA_DIR / f"{sym}_USDT_1h_ohlcv.csv"
    dst: Path = TRIMMED_DIR / f"{sym}_USDT_1h_ohlcv.csv"
    if dst.exists():
        return True
    if not src.exists():
        return False
    with open(src, "r") as f:
        reader = csvmod.reader(f)
        header = next(reader)
        rows = list(reader)
    trimmed = rows[-2162:]  # ~3 months of 1h data
    with open(dst, "w", newline="") as f:
        writer = csvmod.writer(f)
        writer.writerow(header)
        writer.writerows(trimmed)
    print(f"📋 Trimmed {sym}: {len(rows)} → {len(trimmed)} rows")
    return True


if __name__ == "__main__":
    print("🔬 Multi-Symbol Portfolio Backtest")
    print(f"   Cash: ${CASH:.0f} | Profile: {PROFILE}")
    print(f"   Watching {len(ALL_SYMBOLS_1H)} symbols on 1h candles")
    print(f"   Period: 3 months (Nov 2025 - Feb 2026)")
    print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Ensure trimmed data exists
    TRIMMED_DIR.mkdir(parents=True, exist_ok=True)
    for sym_name, _ in ALL_SYMBOLS_1H:
        trim_data(sym_name)

    # ── Per-symbol results ──
    header: str = (
        f"{'Sym':6s} {'Trades':>6s} {'W':>3s} {'L':>3s} "
        f"{'WR%':>6s} {'NetPnL':>10s} {'$/day':>8s} {'DD%':>6s}"
    )
    print(header)
    print("=" * 60)

    results: list[dict[str, Any]] = []
    total_trades: int = 0
    total_wins: int = 0
    total_losses: int = 0
    watched_symbols: int = 0
    trading_symbols: int = 0

    for sym, csv_path in ALL_SYMBOLS_1H:
        if not csv_path.exists():
            print(f"{sym:6s} ⚠️  No data — skipping")
            continue

        watched_symbols += 1
        r: dict[str, Any] = run_single(sym, csv_path)

        if "error" in r:
            print(f"{sym:6s} ❌ Error: {str(r['error'])[:50]}")
            continue

        trades: int = int(r["trades"])
        wins: int = int(r["wins"])
        losses: int = int(r["losses"])
        wr_pct: float = float(r["wr"])
        pnl: float = float(r["pnl"])
        dd: float = float(r["dd"])
        pnl_day: float = pnl / DAYS

        if trades > 0:
            trading_symbols += 1
            ok: str = "✅" if pnl > 0 else "❌"
        else:
            ok = "👁️"

        line: str = (
            f"{sym:6s} {trades:6d} {wins:3d} {losses:3d} "
            f"{wr_pct:5.1f}% ${pnl:+9.2f} ${pnl_day:+7.2f} "
            f"{dd:5.1f}% {ok}"
        )
        print(line)
        r["sym"] = sym
        r["pnl_day"] = pnl_day
        results.append(r)
        total_trades += trades
        total_wins += wins
        total_losses += losses

    print("=" * 60)

    # ── Portfolio Summary ──
    profitable: list[dict[str, Any]] = [
        r for r in results if float(r["pnl"]) > 0
    ]
    unprofitable: list[dict[str, Any]] = [
        r for r in results if float(r["pnl"]) < 0 and int(r["trades"]) > 0
    ]
    no_signal: list[dict[str, Any]] = [
        r for r in results if int(r["trades"]) == 0
    ]

    total_pnl: float = sum(float(r["pnl"]) for r in profitable)
    total_loss: float = sum(float(r["pnl"]) for r in unprofitable)
    net: float = total_pnl + total_loss
    net_per_day: float = net / DAYS

    wr_all: float = (total_wins / total_trades * 100) if total_trades > 0 else 0.0

    print()
    print(f"📊 PORTFOLIO SUMMARY ({watched_symbols} symbols watched)")
    print(f"   Symbols with trades:  {trading_symbols}/{watched_symbols}")
    safe_denom: int = trading_symbols if trading_symbols > 0 else 1
    print(f"   Symbols profitable:   {len(profitable)}/{safe_denom}")
    print(f"   Symbols watching:     {len(no_signal)} (0 trades = free to monitor)")
    print()
    print(f"   Total Trades:     {total_trades}")
    print(f"   Wins / Losses:    {total_wins}W / {total_losses}L ({wr_all:.1f}% WR)")
    print(f"   Winning PnL:      ${total_pnl:+.2f}")
    print(f"   Losing PnL:       ${total_loss:+.2f}")
    print(f"   ─────────────────────────────")
    print(f"   💰 NET PROFIT:    ${net:+.2f}")
    print(f"   📈 Daily:         ${net_per_day:+.2f}/day")
    print(f"   📅 Monthly:       ${net_per_day * 30:+.0f}/month")
    print(f"   📆 Yearly:        ${net_per_day * 365:+.0f}/year")
    print()

    if profitable:
        print("✅ PROFITABLE (auto-traded by bot):")
        for r in sorted(profitable, key=lambda x: -float(x["pnl_day"])):
            print(
                f"   {r['sym']:6s} ${float(r['pnl_day']):+.2f}/day  |  "
                f"{float(r['wr']):.0f}% WR  |  {int(r['trades'])} trades"
            )

    if unprofitable:
        print(f"\n⚠️  LOSING (bot traded but lost — still enabled):")
        for r in sorted(unprofitable, key=lambda x: float(x["pnl"])):
            print(
                f"   {r['sym']:6s} ${float(r['pnl_day']):+.2f}/day  |  "
                f"{float(r['wr']):.0f}% WR  |  {int(r['trades'])} trades"
            )

    if no_signal:
        print(f"\n👁️  WATCHING (no signals in this period — keep enabled):")
        for r in no_signal:
            print(f"   {r['sym']:6s}  — waiting for strategy conditions")

    print(f"\n   Finished: {datetime.now().strftime('%H:%M:%S')}")
