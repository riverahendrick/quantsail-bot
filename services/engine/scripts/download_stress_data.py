"""Download historical data for stress testing across multiple market regimes.

Downloads 1h OHLCV data for BTC, ETH, SOL across 4 market regimes:
  - 2022 Bear Market (Jan-Dec): BTC $48K -> $16K
  - 2023 Recovery   (Jan-Dec): BTC $16K -> $42K
  - 2024 Range      (Jan-Dec): BTC $42K -> $96K
  - 2025 Current    (already have in data/historical/)

Usage:
    python scripts/download_stress_data.py
"""

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import ccxt
except ImportError:
    print("ccxt required: pip install ccxt")
    sys.exit(1)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical" / "stress_test"

# Market regimes to download
REGIMES: list[dict] = [
    {
        "name": "2022_bear",
        "label": "2022 Crypto Winter (Bear Market)",
        "start": "2022-01-01T00:00:00Z",
        "end": "2022-12-31T23:00:00Z",
    },
    {
        "name": "2023_recovery",
        "label": "2023 Recovery Rally",
        "start": "2023-01-01T00:00:00Z",
        "end": "2023-12-31T23:00:00Z",
    },
    {
        "name": "2024_range",
        "label": "2024 Accumulation / Range",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-12-31T23:00:00Z",
    },
]

SYMBOLS: list[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TIMEFRAME = "1h"


def download_range(
    exchange: object,
    symbol: str,
    timeframe: str,
    start_iso: str,
    end_iso: str,
) -> list[list]:
    """Download OHLCV data for a specific date range with pagination."""
    start_ms = int(datetime.fromisoformat(start_iso.replace("Z", "+00:00")).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(end_iso.replace("Z", "+00:00")).timestamp() * 1000)

    all_candles: list[list] = []
    current_since = start_ms

    while current_since < end_ms:
        try:
            candles = exchange.fetch_ohlcv(  # type: ignore[attr-defined]
                symbol, timeframe, since=current_since, limit=1000
            )
            if not candles:
                break

            # Filter to only include candles within our range
            filtered = [c for c in candles if c[0] <= end_ms]
            all_candles.extend(filtered)

            last_ts = candles[-1][0]
            progress = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
            print(f"     {progress.strftime('%Y-%m-%d %H:%M')} "
                  f"({len(all_candles)} candles)")

            current_since = last_ts + 1

            if len(candles) < 1000 or last_ts >= end_ms:
                break

            time.sleep(0.5)  # Be nice to the API

        except Exception as e:
            print(f"     Error: {e}, retrying...")
            time.sleep(2)
            continue

    return all_candles


def save_csv(candles: list[list], filepath: Path) -> None:
    """Save OHLCV candles to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for c in candles:
            writer.writerow([
                datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc).isoformat(),
                c[1], c[2], c[3], c[4], c[5],
            ])
    print(f"     Saved {len(candles)} candles -> {filepath.name}")


def main() -> None:
    """Download stress test data for all regimes and symbols."""
    print("=" * 60)
    print("STRESS TEST DATA DOWNLOADER")
    print("=" * 60)
    print(f"Output: {DATA_DIR}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframe: {TIMEFRAME}")
    print()

    exchange = ccxt.binance({
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })

    total_files = 0
    for regime in REGIMES:
        print(f"\n{'='*60}")
        print(f"Regime: {regime['label']}")
        print(f"Period: {regime['start'][:10]} to {regime['end'][:10]}")
        print(f"{'='*60}")

        regime_dir = DATA_DIR / regime["name"]

        for symbol in SYMBOLS:
            safe = symbol.replace("/", "_")
            filepath = regime_dir / f"{safe}_{TIMEFRAME}_ohlcv.csv"

            if filepath.exists():
                print(f"  {symbol}: already downloaded, skipping")
                continue

            print(f"  {symbol}: downloading...")
            candles = download_range(
                exchange, symbol, TIMEFRAME,
                regime["start"], regime["end"],
            )

            if candles:
                save_csv(candles, filepath)
                total_files += 1

                first_close = candles[0][4]
                last_close = candles[-1][4]
                change_pct = (last_close - first_close) / first_close * 100
                print(f"     Price: ${first_close:,.2f} -> ${last_close:,.2f} "
                      f"({change_pct:+.1f}%)")
            else:
                print(f"     No data available")

            time.sleep(1)  # Rate limit between symbols

    print(f"\nDone! Downloaded {total_files} new files.")


if __name__ == "__main__":
    main()
