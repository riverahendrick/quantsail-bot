"""Historical OHLCV data downloader for backtesting.

Usage:
    python -m tools.download_data --symbol BTC/USDT --timeframe 1m --days 30
    python -m tools.download_data --symbol ETH/USDT --timeframe 5m --days 60 --output ./data
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import ccxt

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download historical OHLCV data for backtesting"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC/USDT",
        help="Trading pair symbol (e.g., BTC/USDT)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1m",
        help="Candle timeframe (e.g., 1m, 5m, 15m, 1h, 4h, 1d)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of historical data to download",
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default="binance",
        help="Exchange to fetch data from (default: binance)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for data files (default: ./data)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "parquet"],
        default="csv",
        help="Output format (default: csv)",
    )
    return parser.parse_args()


def download_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str,
    days: int,
) -> list[list]:
    """Download OHLCV data from exchange.

    Args:
        exchange_id: Exchange identifier (e.g., 'binance')
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '1m', '5m', '1h')
        days: Number of days of data to download

    Returns:
        List of OHLCV candles [timestamp, open, high, low, close, volume]
    """
    print(f"📊 Initializing {exchange_id} exchange...")
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        }
    })

    # Calculate time range
    now = datetime.now(timezone.utc)
    since = int((now.timestamp() - days * 24 * 60 * 60) * 1000)

    print(f"⬇️  Downloading {symbol} {timeframe} data for last {days} days...")
    print(f"   From: {datetime.fromtimestamp(since/1000, tz=timezone.utc).isoformat()}")
    print(f"   To:   {now.isoformat()}")

    all_candles: list[list] = []
    current_since = since

    # CCXT has rate limiting, but we'll be nice and fetch in chunks
    # Most exchanges return 500-1000 candles per request
    while current_since < int(now.timestamp() * 1000):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            if not candles:
                break

            all_candles.extend(candles)
            last_timestamp = candles[-1][0]

            # Progress indicator
            progress_date = datetime.fromtimestamp(last_timestamp / 1000, tz=timezone.utc)
            print(f"   Fetched {len(candles)} candles, last: {progress_date.strftime('%Y-%m-%d %H:%M')}")

            # Move to next batch (add 1ms to avoid duplicates)
            current_since = last_timestamp + 1

            # Stop if we've reached the end
            if len(candles) < 1000:
                break

        except ccxt.NetworkError as e:
            print(f"⚠️  Network error: {e}. Retrying...")
            continue
        except ccxt.ExchangeError as e:
            print(f"❌ Exchange error: {e}")
            raise

    print(f"✅ Downloaded {len(all_candles)} total candles")
    return all_candles


def save_to_csv(
    candles: list[list],
    symbol: str,
    timeframe: str,
    output_dir: Path,
) -> Path:
    """Save candles to CSV file.

    Args:
        candles: List of OHLCV candles
        symbol: Trading pair symbol
        timeframe: Candle timeframe
        output_dir: Output directory

    Returns:
        Path to saved file
    """
    # Create safe filename
    safe_symbol = symbol.replace("/", "_")
    filename = f"{safe_symbol}_{timeframe}_ohlcv.csv"
    filepath = output_dir / filename

    print(f"💾 Saving to CSV: {filepath}")

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        for candle in candles:
            writer.writerow([
                datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc).isoformat(),
                candle[1],
                candle[2],
                candle[3],
                candle[4],
                candle[5],
            ])

    print(f"✅ Saved {len(candles)} candles to {filepath}")
    return filepath


def save_to_parquet(
    candles: list[list],
    symbol: str,
    timeframe: str,
    output_dir: Path,
) -> Path:
    """Save candles to Parquet file.

    Args:
        candles: List of OHLCV candles
        symbol: Trading pair symbol
        timeframe: Candle timeframe
        output_dir: Output directory

    Returns:
        Path to saved file
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("⚠️  pyarrow not installed. Falling back to CSV format.")
        print("   Install with: pip install pyarrow")
        return save_to_csv(candles, symbol, timeframe, output_dir)

    # Create safe filename
    safe_symbol = symbol.replace("/", "_")
    filename = f"{safe_symbol}_{timeframe}_ohlcv.parquet"
    filepath = output_dir / filename

    print(f"💾 Saving to Parquet: {filepath}")

    # Convert to PyArrow table
    timestamps = [datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc) for c in candles]
    opens = [c[1] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    volumes = [c[5] for c in candles]

    table = pa.table({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })

    pq.write_table(table, filepath)

    print(f"✅ Saved {len(candles)} candles to {filepath}")
    return filepath


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        # Default to project_root/data
        output_dir = Path(__file__).parent.parent.parent.parent / "data"

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download data
        candles = download_ohlcv(
            exchange_id=args.exchange,
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
        )

        if not candles:
            print("❌ No data downloaded")
            return 1

        # Save data
        if args.format == "csv":
            filepath = save_to_csv(candles, args.symbol, args.timeframe, output_dir)
        else:
            filepath = save_to_parquet(candles, args.symbol, args.timeframe, output_dir)

        # Print summary
        print("\n📈 Data Summary:")
        print(f"   Symbol:     {args.symbol}")
        print(f"   Timeframe:  {args.timeframe}")
        print(f"   Candles:    {len(candles)}")
        print(f"   Start:      {datetime.fromtimestamp(candles[0][0]/1000, tz=timezone.utc).isoformat()}")
        print(f"   End:        {datetime.fromtimestamp(candles[-1][0]/1000, tz=timezone.utc).isoformat()}")
        print(f"   File:       {filepath}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
