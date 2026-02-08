"""Trade-level diagnostic for profitability analysis."""
import sys
import io
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
OUT_FILE = Path(__file__).resolve().parent / "trade_diagnostics.txt"
CASH = 5000.0

lines: list[str] = []

for profile in ["aggressive", "conservative"]:
    for sym, csv in [("BTC", "BTCUSDT_5m.csv"), ("ETH", "ETHUSDT_5m.csv"),
                     ("SOL", "SOLUSDT_5m.csv"), ("BNB", "BNBUSDT_5m.csv")]:
        dp = DATA_DIR / csv
        if not dp.exists():
            continue
        base = BotConfig()
        tuned = apply_profile(base.model_dump(), profile)
        config = BotConfig(**tuned)
        old = sys.stdout
        sys.stdout = io.StringIO()
        runner = BacktestRunner(config=config, data_file=dp, starting_cash=CASH)
        m = runner.run()
        sys.stdout = old

        trades = runner.repository.get_all_trades()
        events = runner.repository.get_events()
        exit_events = [e for e in events if e.get("event_type") == "trade.exit"]

        lines.append(f"\n=== {profile} / {sym} === {len(trades)} trades ===")
        lines.append(f"  Win rate: {m.win_rate_pct:.1f}% | Net PnL: ${m.net_profit_usd:.2f}")
        lines.append(f"  SL config: ATR mult={config.stop_loss.atr_multiplier}")
        lines.append(f"  TP config: R:R={config.take_profit.risk_reward_ratio}")
        lines.append(f"  Trailing: activation={config.trailing_stop.activation_pct}%")

        wins = []
        losses = []
        for t in trades:
            if t.get("status") != "CLOSED":
                continue
            
            pnl = t.get("realized_pnl_usd")
            if pnl is None:
                pnl = t.get("pnl_usd", 0)
            
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(pnl)
            
            entry_price = t.get("entry_price") or 0.0
            exit_price = t.get("exit_price") or 0.0
            lines.append(f"  PnL=${pnl:+.4f} entry={entry_price:.2f} exit={exit_price:.2f}")

        # Exit event analysis
        exit_reasons: dict[str, int] = {}
        for e in exit_events:
            reason = e.get("payload", {}).get("reason", "unknown")
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        lines.append(f"  Exit reasons: {exit_reasons}")

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        lines.append(f"  Avg win: ${avg_win:.4f} ({len(wins)} trades)")
        lines.append(f"  Avg loss: ${avg_loss:.4f} ({len(losses)} trades)")
        if avg_loss != 0:
            lines.append(f"  Actual R:R achieved: {abs(avg_win / avg_loss):.2f}")

        runner.close()

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
