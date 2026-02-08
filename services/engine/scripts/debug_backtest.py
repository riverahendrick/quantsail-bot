"""Debug script: run backtest and inspect trade planning diagnostics."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

# Enable DEBUG logging for the runner module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-30s %(levelname)-5s %(message)s",
)
# Quiet down noisy modules, keep runner + position sizer verbose
logging.getLogger("quantsail_engine.backtest.runner").setLevel(logging.DEBUG)
logging.getLogger("quantsail_engine.execution.position_sizer").setLevel(logging.DEBUG)

DATA = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "historical"
    / "BTCUSDT_5m.csv"
)
if not DATA.exists():
    print(f"ERROR: Data file not found at {DATA}")
    sys.exit(1)

PROFILE = "aggressive"
STARTING_CASH = 5000.0

print(f"=== Debug Backtest ===")
print(f"  Profile:  {PROFILE}")
print(f"  Cash:     ${STARTING_CASH:,.0f}")
print(f"  Data:     {DATA.name}")
print()

base = BotConfig()
tuned_dict = apply_profile(base.model_dump(), PROFILE)
config = BotConfig(**tuned_dict)

# Print key config values
print(f"  SL method:     {config.stop_loss.method}")
print(f"  SL fixed_pct:  {config.stop_loss.fixed_pct}%")
print(f"  SL ATR period: {config.stop_loss.atr_period} x {config.stop_loss.atr_multiplier}")
print(f"  TP method:     {config.take_profit.method}")
print(f"  TP fixed_pct:  {config.take_profit.fixed_pct}%")
print(f"  TP R:R ratio:  {config.take_profit.risk_reward_ratio}")
print(f"  Min profit:    ${config.execution.min_profit_usd}")
print(f"  Max risk/trade: {config.risk.max_risk_per_trade_pct}%")
print()

runner = BacktestRunner(config=config, data_file=DATA, starting_cash=STARTING_CASH)
metrics = runner.run()

# Inspect all events for sizing/profitability info
events = runner.repository.get_events()
sizing_rejected = [e for e in events if e.get("event_type") == "gate.sizing.rejected"]
profit_rejected = [e for e in events if e.get("event_type") == "gate.profitability.rejected"]
profit_passed = [e for e in events if e.get("event_type") == "gate.profitability.passed"]

print(f"\n=== Event Summary ===")
print(f"  Sizing rejected:       {len(sizing_rejected)}")
print(f"  Profitability rejected: {len(profit_rejected)}")
print(f"  Profitability passed:   {len(profit_passed)}")

# Show first few sizing rejections
if sizing_rejected:
    print(f"\n  First 3 sizing rejections:")
    for e in sizing_rejected[:3]:
        p = e.get("payload", {})
        print(f"    entry=${p.get('entry', 0):,.2f}  sl=${p.get('sl', 0):,.2f}  "
              f"tp=${p.get('tp', 0):,.2f}  equity=${p.get('equity', 0):,.2f}")

# Show first few profitability passes
if profit_passed:
    print(f"\n  First 3 profitability passes:")
    for e in profit_passed[:3]:
        print(f"    {e.get('payload', {})}")

# Debug: inspect what get_all_trades returns
trades = runner.repository.get_all_trades()
print(f"\n=== Trade Results ===")
print(f"  Total trades: {len(trades)}")
for i, t in enumerate(trades):
    status = t.get("status", "UNKNOWN")
    pnl = t.get("realized_pnl_usd")
    exit_p = t.get("exit_price")
    entry_p = t.get("entry_price")
    qty = t.get("quantity")
    sl = t.get("stop_loss_price")
    tp = t.get("take_profit_price")
    print(
        f"  #{i+1}: status={status}  entry=${entry_p}  exit=${exit_p}  "
        f"qty={qty}  sl=${sl}  tp=${tp}  pnl=${pnl}"
    )

print(f"\n=== Metrics ===")
print(f"  total_trades:   {metrics.total_trades}")
print(f"  winning:        {metrics.winning_trades}")
print(f"  losing:         {metrics.losing_trades}")
print(f"  net_profit:     ${metrics.net_profit_usd:.2f}")
print(f"  end_equity:     ${metrics.end_equity:.2f}")
print(f"  win_rate:       {metrics.win_rate_pct:.1f}%")
print(f"  max_drawdown:   {metrics.max_drawdown_pct:.2f}%")

runner.close()
