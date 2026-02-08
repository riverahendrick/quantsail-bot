"""Diagnostic script: trace what each strategy outputs per tick.

Runs a simplified version of the backtest loop, printing strategy 
outputs for each tick so we can see *why* zero trades are generated.
"""

import sys
from pathlib import Path

# Ensure quantsail_engine is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter

from quantsail_engine.backtest.market_provider import BacktestMarketProvider
from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.config.models import BotConfig
from quantsail_engine.models.signal import SignalType
from quantsail_engine.strategies.ensemble import EnsembleCombiner

DEFAULT_DATA = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical" / "BTCUSDT_5m.csv"


def diagnose(data_file: str | Path = DEFAULT_DATA, max_ticks: int = 500) -> None:
    """Run diagnosis on strategy signals."""
    data_path = Path(data_file)
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return

    config = BotConfig()
    time_manager = TimeManager()
    symbol = config.symbols.enabled[0]

    market = BacktestMarketProvider(
        data_file=data_path,
        time_manager=time_manager,
        symbol=symbol,
    )

    combiner = EnsembleCombiner()

    # Track stats
    strategy_signal_counts: dict[str, Counter] = {}
    ensemble_signal_counts: Counter = Counter()
    long_detail_ticks: list[dict] = []  # ticks where at least 1 strategy said ENTER_LONG
    tick_count = 0

    print(f"📊 Diagnosing signal generation")
    print(f"   Data: {data_path}")
    print(f"   Symbol: {symbol}")
    print(f"   Ensemble mode: {config.strategies.ensemble.mode}")
    print(f"   Min agreement: {config.strategies.ensemble.min_agreement}")
    print(f"   Confidence threshold: {config.strategies.ensemble.confidence_threshold}")
    print()

    for timestamp in market.iter_timestamps(300):
        time_manager.set_time(timestamp)
        tick_count += 1
        if tick_count > max_ticks:
            break

        try:
            candles = market.get_candles(symbol, "5m", 100)
        except (ValueError, IndexError):
            continue

        if len(candles) < 30:
            continue  # not enough history for indicators

        try:
            orderbook = market.get_orderbook(symbol, depth_levels=5)
        except Exception:
            continue

        signal = combiner.analyze(symbol, candles, orderbook, config)

        # Track ensemble signal
        ensemble_signal_counts[signal.signal_type] += 1

        # Track per-strategy
        any_long = False
        tick_info = {"tick": tick_count, "ts": str(timestamp)}
        for out in signal.strategy_outputs:
            name = out.strategy_name
            if name not in strategy_signal_counts:
                strategy_signal_counts[name] = Counter()
            strategy_signal_counts[name][out.signal] += 1
            tick_info[name] = {
                "signal": str(out.signal),
                "confidence": round(out.confidence, 4),
            }
            if out.signal == SignalType.ENTER_LONG:
                any_long = True

        if any_long:
            long_detail_ticks.append(tick_info)

        # Print occasional progress
        if tick_count % 100 == 0:
            print(f"   Tick {tick_count} processed...")

    # Print results
    print(f"\n{'='*60}")
    print(f"  DIAGNOSIS RESULTS ({tick_count} ticks analyzed)")
    print(f"{'='*60}\n")

    print("── Per-Strategy Signal Distribution ──")
    for name, counts in sorted(strategy_signal_counts.items()):
        print(f"\n  {name}:")
        for sig, count in counts.most_common():
            pct = count / tick_count * 100
            print(f"    {sig}: {count} ({pct:.1f}%)")

    print(f"\n── Ensemble Final Signal Distribution ──")
    for sig, count in ensemble_signal_counts.most_common():
        pct = count / tick_count * 100
        print(f"  {sig}: {count} ({pct:.1f}%)")

    print(f"\n── Ticks Where At Least 1 Strategy Said ENTER_LONG ──")
    if long_detail_ticks:
        for detail in long_detail_ticks[:20]:  # show first 20
            print(f"  Tick {detail['tick']} ({detail['ts']}):")
            for k, v in detail.items():
                if k in ("tick", "ts"):
                    continue
                print(f"    {k}: {v['signal']:12s} conf={v['confidence']}")
        if len(long_detail_ticks) > 20:
            print(f"  ... and {len(long_detail_ticks) - 20} more")
    else:
        print("  ⚠️  NONE — no strategy ever produced ENTER_LONG!")

    print(f"\n  Total ticks with ≥1 ENTER_LONG: {len(long_detail_ticks)} / {tick_count}")


if __name__ == "__main__":
    data = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_DATA)
    diagnose(data_file=data)
