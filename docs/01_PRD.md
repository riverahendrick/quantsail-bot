# Quantsail — Product Requirements Document (PRD) v6
**Date:** 2026-01-26  
**MVP:** Binance **crypto spot** only. Dry‑run first. Exchange‑agnostic architecture so Coinbase can be added later.  
**Dashboards:** Private operator console + Public transparency pages (sanitized).

---

## 0) Read First (Non‑Negotiable)
- Every contributor must read `GLOBAL_RULES.md` and follow it.
- The system must be **safe-by-default**: dry‑run mode is default; live trading requires explicit arming.

---

## 1) Product Goal and Reality Check
### 1.1 Goal (target, not a promise)
- The operator can configure a daily profit target (e.g., **$1–$2/day** on $1k–$5k).
- The system reports results **net of fees and estimated slippage**.
- The system provides safety controls that reduce the probability of ending the day red (daily lock, breakers, strict profitability gating).

### 1.2 What we can and cannot guarantee
- Markets are stochastic. No architecture can guarantee a green day every day.
- We **can** design for disciplined behavior: do not trade low-edge setups; stop after hitting target; pause during shocks; limit drawdowns; ensure exits remain managed.

**Engineering requirement:** all docs and UI must describe this accurately (no misleading profit guarantees).

---

## 2) Personas and Use Cases
### 2.1 Owner/CTO (primary)
- Adds exchange keys
- Configures symbols/strategies/risk/gates
- Arms live trading (later)
- Monitors performance and incidents
- Exports reports

### 2.2 CEO (secondary)
- Views private dashboard read-only
- Can pause entries (optional permission)
- Views public transparency performance

### 2.3 Public viewer (external)
- Views sanitized performance pages and a delayed trade/event feed
- Never sees secrets, account identity, or exact position sizes (optional bucketing)

---

## 3) Core Requirements Summary (MVP)
### 3.1 Trading mode
- Default: **dry‑run** (paper)
- Live: supported only after ARM LIVE milestone (later prompt)

### 3.2 Market scope
- Crypto spot, quote assets: USDT/USDC (config allowlist)

### 3.3 Symbols
- User selects a list of symbols.
- Engine scans each symbol on a configurable cadence.

### 3.4 Signal logic
- At least 3 strategies (trend / mean reversion / breakout)
- Ensemble agreement gating (e.g., 2 of 3 must agree)
- Each decision must record rationale and numeric evidence

### 3.5 Profitability gate (critical)
- Before entry, compute:
  - expected gross profit at TP
  - subtract fees + slippage + spread cost estimate
- Reject if expected net profit < `execution.min_profit_usd`

### 3.6 Risk and exits
- Risk-based position sizing
- Stop-loss and take-profit required for every trade
- Exits must never be blocked by entry pauses

### 3.7 Safety controls (critical)
- Circuit breakers: volatility, spread/slippage, consecutive losses, exchange instability
- News shock pause: negative high-impact only (does not “predict” trades)
- Daily target lock: STOP or OVERDRIVE with trailing floor

### 3.8 Transparency (critical)
- Event log is the source of truth (“if a decision happens, it must be an event”)
- Public endpoints return only sanitized data

---

## 4) Functional Requirements (Detailed) — With Acceptance Criteria
> Each item below is written so a developer/AI agent does not have to guess.

### 4.1 Exchange Keys (Binance) — Encrypted and RBAC protected
**User story:** As Owner/CTO, I can add Binance keys safely so the bot can trade.

**Requirements**
- Keys stored encrypted at rest (AES‑GCM)
- Only authorized roles can add/revoke keys
- No secrets in logs, events, UI, or public endpoints

**Acceptance criteria**
- [ ] Saving keys works; retrieving keys works
- [ ] Decrypt is only performed inside VPS runtime (engine/api)
- [ ] Attempting to view raw secrets via API is impossible (no endpoint returns them)
- [ ] Unit tests verify encryption is randomized and decrypt fails on tampering
- [ ] Audit events emitted:
  - `security.key.added` (public_safe=false)
  - `security.key.revoked` (public_safe=false)

---

### 4.2 Config Versioning (Single source of truth)
**User story:** As Owner/CTO, I can change settings safely and roll back.

**Requirements**
- Config stored in DB as versions
- One “active” config version at a time
- Engine reloads config on activation
- Activation emits an event with version and diff summary (no secrets)

**Acceptance criteria**
- [ ] Create config version and activate it
- [ ] Engine picks up new active version within 10 seconds or on next loop tick
- [ ] Tests cover invalid config rejection
- [ ] Event: `config.activated` with version and diff keys

---

### 4.3 Strategy Outputs (Standard schema) + Ensemble Agreement Gating
**User story:** As Owner/CTO, I want multiple strategies to confirm a trade idea.

**Strategy minimum set (MVP)**
1) Trend: EMA cross + ADX filter (example)
2) Mean reversion: Bollinger + RSI mean reversion
3) Breakout: Donchian breakout + ATR filter

**Standard output schema**
- strategy_id, symbol, timeframes_used
- signal: ENTER_LONG | HOLD | EXIT | NO_TRADE
- confidence: 0..1
- suggested_entry, suggested_stop, suggested_take_profit
- rationale object (indicator values, thresholds, “why”)

**Ensemble rule**
- Ensemble takes the strategies’ outputs and decides final action.
- Must record which strategies agreed and why the others disagreed.

**Acceptance criteria**
- [ ] Each strategy is deterministic on fixtures
- [ ] Ensemble respects `strategies.ensemble.min_agreement`
- [ ] Event: `signal.generated` (per strategy) and `ensemble.decision` (aggregate)

---

### 4.4 Fee + Slippage + Spread Profitability Gate (Critical)
**User story:** As Owner/CTO, I do not want trades that look profitable but are not net profitable.

**Requirements**
- Fee model (maker/taker bps) from config
- Slippage estimate from orderbook depth for intended size
- Spread cost estimate (best ask - best bid)
- Expected net profit must exceed `execution.min_profit_usd`

**Acceptance criteria**
- [ ] Trades are rejected when net profit is below threshold
- [ ] Gate emits:
  - `gate.profitability.passed`
  - `gate.profitability.rejected`
  including breakdown: gross, fee, slippage, spread, net
- [ ] Unit tests cover low liquidity, high spread, high fee scenarios

---

### 4.5 Risk Sizing + Exits (SL/TP mandatory)
**User story:** As Owner/CTO, I can control risk per trade and ensure exits exist.

**Requirements**
- Risk per trade percent of equity
- Max position percent of equity
- Min notional
- For every entry, compute and persist:
  - SL price
  - TP price
- Trailing stop optional (off by default)

**Acceptance criteria**
- [ ] Position sizing math is tested and correct
- [ ] Every opened trade has SL/TP persisted
- [ ] Exits continue even if entries are paused

---

### 4.6 Circuit Breakers (Pause entries, never block exits)
Breakers and default behavior:
- Volatility spike → pause entries N minutes
- Spread/slippage spike → pause entries N minutes
- Consecutive losses → pause entries longer
- Exchange instability (disconnects/rate limits) → pause entries
- News negative shock (high impact) → pause entries

**Acceptance criteria**
- [ ] Breakers trigger and expire per config
- [ ] Entry logic respects breaker state
- [ ] Exit logic bypasses breaker state
- [ ] Events: `breaker.triggered`, `breaker.expired`

---

### 4.7 Daily Target Lock (STOP / OVERDRIVE + trailing floor)
**User story:** As Owner/CTO, once we hit a daily profit goal, I want the bot to stop or protect profits.

**Definitions**
- realized_pnl_today_usd = sum of closed trade pnl for “today” in configured timezone
- daily_target_usd = operator-defined target
- mode:
  - STOP: stop new entries after reaching target
  - OVERDRIVE: keep trading but maintain a profit floor

**OVERDRIVE rules**
- Track peak_realized_pnl_today_usd
- floor = max(daily_target_usd, peak - trailing_buffer)
- If realized falls to floor → stop new entries (optional force close based on config)

**Acceptance criteria**
- [ ] Tests cover: reach target → continue → reach peak → floor moves → drawdown to floor → entries pause
- [ ] Events: `daily_lock.engaged`, `daily_lock.floor_updated`, `daily_lock.entries_paused`

---

### 4.8 Transparency + Dashboards
**Private dashboard must show**
- bot status (running/paused/stopped + reason + until)
- today PnL and daily lock widget
- open positions, recent trades
- “why” panel: last ensemble decision and last gate rejection reasons
- event timeline with filters

**Public dashboard must show (sanitized)**
- headline metrics and equity curve
- sanitized trade feed (no exchange IDs; optional size buckets; optional time delay)
- transparency explainer page (“how it works” and “what we hide”)

**Acceptance criteria**
- [ ] Public endpoints never return secrets or identifiers
- [ ] Sanitization tested with unit tests
- [ ] E2E tests cover critical pages

---

## 5) Non‑Functional Requirements (Engineering)
### 5.1 Security
- Secrets encrypted at rest; never logged
- RBAC on private endpoints; rate limit on public
- ARM LIVE two-step gate (later)
- Separate public router and serializers

### 5.2 Reliability
- Restart-safe reconciliation
- Idempotent order placement (later)
- Resilient to exchange disconnects (retry/backoff)
- Event journal append-only

### 5.3 Testing policy (mandatory)
- TDD
- 100% coverage for touched files
- Integration tests for DB migrations and engine↔API↔DB
- E2E tests for dashboards

---

## 6) Out of Scope (MVP)
- Futures/leverage
- Multi-tenant user accounts
- Automated “LLM decides trades” (LLM may be used only for explanations, docs, or optional analysis later)

---

## 7) Roadmap (High-level)
- Phase A: Repo + guardrails + schema + RBAC + event journal
- Phase B: Dry-run trading + strategies + gates + breakers + daily lock
- Phase C: Dashboards + public transparency
- Phase D: ARM LIVE + Binance live execution + reconciliation
- Phase E: Coinbase adapter (future) + Forex (future) + Stocks (future)

---

## 8) PRD Completion Checklist
- [ ] Every requirement above has a corresponding test plan
- [ ] Config keys are fully defined in `docs/09_CONFIG_SPEC.md`
- [ ] Engine state machine and interfaces defined in `docs/13_ENGINE_SPEC.md`
- [ ] Event taxonomy is implemented and used everywhere
- [ ] Public sanitization is proven by tests


---

## 9) MVP Done Checklist (from v4, still required)
- [ ] Repo structure matches `docs/02_ARCHITECTURE.md` + `docs/11_FOLDER_STRUCTURE_DETAILED.md`
- [ ] Dry-run end-to-end works (events visible in dashboards)
- [ ] Profitability gate blocks low-edge trades
- [ ] Daily target lock works and is proven by tests
- [ ] Circuit breakers work and are proven by tests
- [ ] Private dashboard operational
- [ ] Public dashboard safe and sanitized
- [ ] Security checklist completed (`docs/06_SECURITY_OPS.md`, threat model)
- [ ] Deployed on VPS + Vercel

## 10) Build-plan mapping
Implementation is executed via `docs/08_PROMPTS/` in order. See `docs/08_PROMPTS/INDEX.md`.
