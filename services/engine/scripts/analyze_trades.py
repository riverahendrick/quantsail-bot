"""Analyze trade logs from previous backtests."""
import csv
from pathlib import Path

scripts_dir = Path(__file__).resolve().parent
symbols = ["BTC", "ETH", "SOL", "BNB", "XRP"]

for sym in symbols:
    trades_file = scripts_dir / f"trades_aggressive_1h_{sym}.csv"
    if not trades_file.exists():
        print(f"{sym}: No trades file found")
        continue

    with open(trades_file, "r") as f:
        reader = csv.DictReader(f)
        trades = list(reader)

    if not trades:
        print(f"{sym}: 0 trades")
        continue

    wins = [t for t in trades if float(t.get("pnl_usd", "0") or "0") > 0]
    losses = [t for t in trades if float(t.get("pnl_usd", "0") or "0") <= 0]

    avg_win = sum(float(w["pnl_usd"] or 0) for w in wins) / max(len(wins), 1)
    avg_loss = sum(float(l["pnl_usd"] or 0) for l in losses) / max(len(losses), 1)
    total_pnl = sum(float(t.get("pnl_usd", "0") or "0") for t in trades)

    print(f"\n{'='*60}")
    print(f"{sym}: {len(trades)} trades | Win: {len(wins)} | Loss: {len(losses)} | WR: {len(wins)/len(trades)*100:.1f}%")
    print(f"  Total PnL: ${total_pnl:+.2f} | Avg Win: ${avg_win:+.2f} | Avg Loss: ${avg_loss:+.2f}")

    # Exit reason breakdown
    reasons = {}
    for t in trades:
        r = t.get("exit_reason", "unknown")
        reasons[r] = reasons.get(r, 0) + 1
    print(f"  Exit reasons: {reasons}")

    # Show individual trades
    for i, t in enumerate(trades):
        pnl = float(t.get("pnl_usd", "0") or "0")
        marker = "✅" if pnl > 0 else "❌"
        print(f"  {marker} #{i+1}: PnL=${pnl:+.2f} | Exit={t.get('exit_reason')} | Entry=${float(t.get('entry_price','0') or '0'):.2f}")
