"""Signal audit: check how many ENTER_LONG signals each strategy produces."""
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.CRITICAL)

from quantsail_engine.config.models import BotConfig
from quantsail_engine.config.parameter_profiles import apply_profile
from quantsail_engine.models.signal import SignalType
from quantsail_engine.strategies.ensemble import EnsembleCombiner
from quantsail_engine.backtest.market_provider import BacktestMarketProvider
from quantsail_engine.backtest.time_manager import TimeManager

DATA = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "historical" / "BTCUSDT_5m.csv"
)
SYMBOL = "BTC/USDT"

# Use aggressive profile (most lenient thresholds)
base = BotConfig()
tuned = apply_profile(base.model_dump(), "aggressive")
config = BotConfig(**tuned)

print(f"Ensemble mode:  {config.strategies.ensemble.mode}")
print(f"min_agreement:  {config.strategies.ensemble.min_agreement}")
print(f"conf_threshold: {config.strategies.ensemble.confidence_threshold}")
print()

# Load via proper provider
time_mgr = TimeManager()
provider = BacktestMarketProvider(
    data_file=DATA, time_manager=time_mgr, symbol=SYMBOL
)
combiner = EnsembleCombiner()

# Counters
strategy_signals: dict[str, Counter] = {}
ensemble_signals: Counter = Counter()
confidence_buckets: dict[str, list[float]] = {}
total_ticks = 0

# Iterate through candles
for ts in provider.iter_timestamps(interval_seconds=300):
    time_mgr.set_time(ts)

    try:
        candles = provider.get_candles(SYMBOL, "5m", limit=100)
    except ValueError:
        continue

    if len(candles) < 30:
        continue

    try:
        orderbook = provider.get_orderbook(SYMBOL, 5)
    except ValueError:
        continue

    try:
        signal = combiner.analyze(SYMBOL, candles, orderbook, config)
    except Exception:
        continue

    total_ticks += 1

    # Count ensemble result
    ensemble_signals[signal.signal_type] += 1

    # Count per strategy
    for output in signal.strategy_outputs:
        name = output.strategy_name
        if name not in strategy_signals:
            strategy_signals[name] = Counter()
            confidence_buckets[name] = []
        strategy_signals[name][output.signal] += 1

        if output.signal == SignalType.ENTER_LONG:
            confidence_buckets[name].append(output.confidence)

print(f"Total ticks analyzed: {total_ticks}")
print()

print("=== Ensemble Final Signals ===")
for sig_type, count in sorted(ensemble_signals.items(), key=lambda x: -x[1]):
    pct = count / total_ticks * 100 if total_ticks else 0
    print(f"  {sig_type!s:15s}: {count:5d}  ({pct:.1f}%)")

print()
print("=== Per-Strategy Breakdown ===")
for name in sorted(strategy_signals.keys()):
    counts = strategy_signals[name]
    print(f"\n  {name}:")
    for sig_type, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count / total_ticks * 100 if total_ticks else 0
        print(f"    {sig_type!s:15s}: {count:5d}  ({pct:.1f}%)")

    longs_conf = confidence_buckets.get(name, [])
    if longs_conf:
        avg = sum(longs_conf) / len(longs_conf)
        print(f"    ENTER_LONG confidences: min={min(longs_conf):.3f}  "
              f"avg={avg:.3f}  max={max(longs_conf):.3f}")
        above_03 = sum(1 for c in longs_conf if c >= 0.3)
        above_05 = sum(1 for c in longs_conf if c >= 0.5)
        above_07 = sum(1 for c in longs_conf if c >= 0.7)
        print(f"    >= 0.3: {above_03}   >= 0.5: {above_05}   >= 0.7: {above_07}")

print("\nDone.")
