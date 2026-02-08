"""Resample 1-minute OHLCV CSVs to 5-minute candles for backtesting."""

import sys
from pathlib import Path

import pandas as pd

INPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
OUTPUT_DIR = INPUT_DIR / "historical"


def resample_1m_to_5m(input_path: Path, output_path: Path) -> int:
    """Resample a 1m OHLCV CSV to 5m and save. Returns row count."""
    df = pd.read_csv(input_path, parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()

    resampled = df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()

    resampled.index.name = "timestamp"
    resampled.to_csv(output_path)
    return len(resampled)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(INPUT_DIR.glob("*_ohlcv.csv"))
    if not csv_files:
        print(f"No CSV files found in {INPUT_DIR}")
        sys.exit(1)

    for csv_path in csv_files:
        # BTC_USDT_1m_ohlcv.csv → BTCUSDT_5m.csv
        parts = csv_path.stem.split("_")  # ['BTC', 'USDT', '1m', 'ohlcv']
        pair = f"{parts[0]}{parts[1]}"
        out_name = f"{pair}_5m.csv"
        out_path = OUTPUT_DIR / out_name

        rows = resample_1m_to_5m(csv_path, out_path)
        print(f"  {csv_path.name} → {out_name}  ({rows} candles)")

    print(f"\nAll files saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
