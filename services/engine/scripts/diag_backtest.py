"""Diagnostic: clean backtest output without debug logger noise."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Suppress all loggers except critical
logging.basicConfig(level=logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "historical" / "BTCUSDT_5m.csv"
)

base = BotConfig()
tuned = apply_profile(base.model_dump(), "aggressive")
config = BotConfig(**tuned)

runner = BacktestRunner(config=config, data_file=DATA, starting_cash=5000.0)
metrics = runner.run()

# Trades
trades = runner.repository.get_all_trades()
print(f"Total trades: {len(trades)}")
for i, t in enumerate(trades):
    print(
        f"  #{i+1}: status={t.get('status'):10s}  "
        f"entry=${t.get('entry_price', 0):>10.2f}  "
        f"exit=${t.get('exit_price', 'N/A')!s:>10s}  "
        f"qty={t.get('quantity', 0):.6f}  "
        f"sl=${t.get('stop_loss_price', 0):>10.2f}  "
        f"tp=${t.get('take_profit_price', 0):>10.2f}  "
        f"pnl=${t.get('realized_pnl_usd', 'N/A')!s:>8s}"
    )

# Events
events = runner.repository.get_events()
event_types = {}
for e in events:
    et = e.get("event_type", "unknown")
    event_types[et] = event_types.get(et, 0) + 1

print(f"\nEvent counts ({len(events)} total):")
for et, count in sorted(event_types.items()):
    print(f"  {et}: {count}")

# Closed trade details
trade_closed = [e for e in events if e.get("event_type") == "trade.closed"]
if trade_closed:
    print(f"\nClosed trade details:")
    for e in trade_closed:
        p = e.get("payload", {})
        print(f"  trade={p.get('trade_id','?')[:8]}  reason={p.get('exit_reason')}  "
              f"exit_price={p.get('exit_price')}  pnl=${p.get('pnl_usd')}")

print(f"\n=== METRICS ===")
print(f"  total_trades: {metrics.total_trades}")
print(f"  winning:      {metrics.winning_trades}")
print(f"  losing:       {metrics.losing_trades}")
print(f"  net_profit:   ${metrics.net_profit_usd:.2f}")
print(f"  end_equity:   ${metrics.end_equity:.2f}")
print(f"  win_rate:     {metrics.win_rate_pct:.1f}%")
print(f"  max_drawdown: {metrics.max_drawdown_pct:.2f}%")

runner.close()
