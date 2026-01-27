# Quantsail — Wireframes (Text)

## Private /app/overview
- Status banner: Running / Paused (reason + until) / Stopped
- KPI cards (grid): Equity, Realized PnL Today, Unrealized PnL, Win rate 30d, Profit factor 30d
- Daily lock card: target, mode, realized, peak, floor, entries paused indicator
- Breakers card: active breakers list + time remaining
- Charts: equity curve, drawdown
- Tables: open positions, recent trades, recent events
- Controls: Start (dry‑run), Stop, Pause entries, Resume entries

## Private /app/strategy
- Strategy toggles, timeframes, ensemble min agreement
- “Last decision” panel (read-only) showing why a trade was taken or rejected

## Private /app/risk
- Risk sliders/inputs + breakers configuration + daily lock configuration

## Private /app/exchange
- Key status, connectivity test button, fee model configuration display

## Private /app/events
- Filters: level/type/symbol/date
- Event drawer for payload (owner only export)

## Public /public/overview
- Simple KPI cards + equity curve + status banner
- Link to transparency explanation

## Public /public/trades
- Sanitized trade feed (optional size buckets)
- Filter by symbol

## Public /public/transparency
- Explain pipeline + gates + breakers + daily lock + what is hidden
