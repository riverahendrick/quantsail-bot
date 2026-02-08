"""Multi-profile, multi-symbol backtest comparison."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.backtest.runner import BacktestRunner

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
PROFILES = ["conservative", "moderate", "aggressive"]
SYMBOLS_MAP = {
    "BTC": "BTCUSDT_5m.csv",
    "ETH": "ETHUSDT_5m.csv",
    "SOL": "SOLUSDT_5m.csv",
    "BNB": "BNBUSDT_5m.csv",
}
STARTING_CASH = 5000.0

print(f"{'Profile':<14} {'Symbol':<6} {'Trades':>6} {'Win':>4} {'Loss':>4} {'Win%':>6} "
      f"{'NetPnL':>10} {'EndEquity':>12} {'MaxDD%':>7}")
print("-" * 80)

for profile in PROFILES:
    for sym_name, csv_file in SYMBOLS_MAP.items():
        data_path = DATA_DIR / csv_file
        if not data_path.exists():
            print(f"{profile:<14} {sym_name:<6}  DATA NOT FOUND: {csv_file}")
            continue

        base = BotConfig()
        tuned = apply_profile(base.model_dump(), profile)
        config = BotConfig(**tuned)

        try:
            runner = BacktestRunner(
                config=config, data_file=data_path, starting_cash=STARTING_CASH
            )
            metrics = runner.run()

            print(
                f"{profile:<14} {sym_name:<6} {metrics.total_trades:>6} "
                f"{metrics.winning_trades:>4} {metrics.losing_trades:>4} "
                f"{metrics.win_rate_pct:>5.1f}% "
                f"${metrics.net_profit_usd:>9.2f} "
                f"${metrics.end_equity:>11.2f} "
                f"{metrics.max_drawdown_pct:>6.2f}%"
            )
            runner.close()
        except Exception as e:
            print(f"{profile:<14} {sym_name:<6}  ERROR: {e}")

print("-" * 80)
print("Done.")
