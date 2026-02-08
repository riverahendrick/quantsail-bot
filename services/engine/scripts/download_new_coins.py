"""Download 1h OHLCV data for new symbols from Binance."""
import csv
import time
import urllib.request
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = [
    "MATICUSDT", "NEARUSDT", "UNIUSDT", "ATOMUSDT",
    "ARBUSDT", "OPUSDT", "SUIUSDT", "APTUSDT",
]
LIMIT = 1000
INTERVAL = "1h"

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)
start_ms = int(start.timestamp() * 1000)
end_ms = int(now.timestamp() * 1000)

print(f"Downloading 1h data for {len(SYMBOLS)} new symbols")
print(f"{start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
print()

for sym in SYMBOLS:
    print(f"  📊 {sym}...", end=" ", flush=True)
    all_k: list = []
    cur = start_ms
    while cur < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines?"
            f"symbol={sym}&interval={INTERVAL}"
            f"&startTime={cur}&endTime={end_ms}&limit={LIMIT}"
        )
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "QuantsailBot/1.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"error: {e}")
            time.sleep(5)
            continue
        if not data:
            break
        all_k.extend(data)
        cur = data[-1][6] + 1
        time.sleep(0.3)

    if all_k:
        base = sym[:-4]
        fname = f"{base}_USDT_{INTERVAL}_ohlcv.csv"
        fpath = DATA_DIR / fname
        with open(fpath, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            for k in all_k:
                ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
                w.writerow([
                    ts.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    k[1], k[2], k[3], k[4], k[5],
                ])
        print(f"✅ {len(all_k)} candles → {fname}")
    else:
        print("❌ no data")

print("\n🎉 Done!")
