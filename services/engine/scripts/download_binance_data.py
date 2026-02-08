"""Download real OHLCV data from Binance public API.

Downloads both 1h and 5m klines for all specified symbols.
No API key required - uses the public endpoint.
"""
import csv
import time
import urllib.request
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Output directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"

# Max candles per request (Binance limit)
LIMIT = 1000


def download_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> list:
    """Download klines from Binance API."""
    all_klines = []
    current_start = start_ms

    while current_start < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines?"
            f"symbol={symbol}&interval={interval}"
            f"&startTime={current_start}&endTime={end_ms}&limit={LIMIT}"
        )

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "QuantsailBot/1.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            time.sleep(5)
            continue

        if not data:
            break

        all_klines.extend(data)

        # Move start to after last candle
        last_close_time = data[-1][6]
        current_start = last_close_time + 1

        if len(all_klines) % 5000 < LIMIT:
            print(f"  ... {len(all_klines)} candles")
        time.sleep(0.3)  # Rate limiting

    return all_klines


def save_to_csv(symbol: str, interval: str, klines: list, output_dir: Path) -> Path:
    """Save klines to CSV in the format expected by the backtester."""
    base = symbol[:-4]  # Remove USDT
    filename = f"{base}_USDT_{interval}_ohlcv.csv"
    output_path = output_dir / filename

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        for k in klines:
            ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
            ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            writer.writerow([ts_str, k[1], k[2], k[3], k[4], k[5]])

    return output_path


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    # ===== 1H DATA (1 year) =====
    symbols_1h = ["ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
    days_1h = 365
    start_1h = now - timedelta(days=days_1h)
    start_ms_1h = int(start_1h.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    print(f"📥 Downloading 1h data ({days_1h} days)")
    print(f"   {start_1h.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print()

    for symbol in symbols_1h:
        print(f"  📊 {symbol} (1h)...")
        klines = download_klines(symbol, "1h", start_ms_1h, end_ms)
        if klines:
            path = save_to_csv(symbol, "1h", klines, DATA_DIR)
            print(f"  ✅ {len(klines)} candles → {path.name}")
        else:
            print(f"  ❌ No data for {symbol}")
        print()

    # ===== 5M DATA (90 days) =====
    # 90 days of 5m = 90 * 24 * 12 = 25,920 candles
    symbols_5m = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
                  "AVAXUSDT", "LINKUSDT"]
    days_5m = 90
    start_5m = now - timedelta(days=days_5m)
    start_ms_5m = int(start_5m.timestamp() * 1000)

    print(f"\n📥 Downloading 5m data ({days_5m} days)")
    print(f"   {start_5m.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print()

    for symbol in symbols_5m:
        print(f"  📊 {symbol} (5m)...")
        klines = download_klines(symbol, "5m", start_ms_5m, end_ms)
        if klines:
            path = save_to_csv(symbol, "5m", klines, DATA_DIR)
            print(f"  ✅ {len(klines)} candles → {path.name}")
        else:
            print(f"  ❌ No data for {symbol}")
        print()

    print("🎉 All downloads complete!")
