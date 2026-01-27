# Quantsail — UI Specification v6 (No Guessing)

## 1) UX principles
- Modern “trading terminal” clarity without clutter
- Always show “why” (last decision + last rejection reasons)
- Strong status banners (running/paused/stopped + reason)
- Accessibility and readability prioritized

## 2) Routes
Private:
- /app/overview
- /app/strategy
- /app/risk
- /app/exchange
- /app/events

Public:
- /public/overview
- /public/trades
- /public/transparency

## 3) Visual expectations (concrete)
- Layout: left sidebar + top bar + responsive grid cards
- Cards: status, equity, pnl today, win rate, profit factor, breakers, daily lock
- Tables: open positions, recent trades, recent events
- Charts: equity curve + drawdown curve
- All pages must work in dark mode first; light mode optional later

## 4) i18n
- Use a central translation system.
- No hardcoded strings. Tests must fail if hardcoded strings are introduced.

## 5) Public vs private separation
- Public pages use ONLY `/public/v1/*` endpoints.
- Private pages use ONLY `/v1/*` endpoints.
- This is enforced in code and validated by tests.
