# 🔍 QUANTSAIL — FULL SYSTEM AUDIT PROMPT

> **Instructions for the Auditing Agent**: Read this prompt in its entirety before beginning. You are performing a deep, comprehensive audit of the **Quantsail** crypto spot auto-trading bot. **Use the actual codebase as the source of truth**, not just documentation — docs may be outdated, incomplete, or aspirational. Read the actual `.py`, `.tsx`, `.ts` files to verify claims.

---

## 🎯 Your Mission

Perform a **full-spectrum technical audit** of the Quantsail project and produce a comprehensive report covering:

1. **What Quantsail IS** — What it does, how it works, what market it targets, who it's for
2. **Architecture & Code Quality** — Deep code review of all 3 services
3. **Deployment Readiness** — Is it ready to run live? What's missing?
4. **Security** — Secrets, auth, encryption, sanitization
5. **Profitability Analysis** — Is the trading logic sound? Can it actually make money?
6. **Dashboard Completeness** — What data from the engine/API is NOT visible in the dashboard?
7. **Operational Readiness** — Logging, monitoring, observability, VPS deployment
8. **Pros & Cons** — Honest assessment of strengths and weaknesses
9. **Recommendations** — Prioritized action items to make this production-ready

---

## 📦 Project Overview (Context for the Auditor)

Quantsail is a self-hosted **crypto spot auto-trading bot** targeting **Binance** (MVP). It has three main components:

| Component | Location | Tech Stack | Deployment |
|-----------|----------|-----------|------------|
| **Engine** | `services/engine/` | Python (uv, Pydantic, SQLAlchemy, ccxt) | VPS |
| **API** | `services/api/` | Python (FastAPI, Alembic, Firebase Auth) | VPS |
| **Dashboard** | `apps/dashboard/` | Next.js (TypeScript, Tailwind, next-intl, Recharts) | Vercel |
| **Database** | `infra/docker/` | Postgres + Redis | VPS (Docker) |

### Decision Pipeline (per symbol)
1. Read market data (candles + order book)
2. Compute indicators across multiple timeframes
3. Run strategies, check if enough agree (ensemble)
4. Apply safety filters (risk limits, circuit breakers, profitability gate)
5. If allowed, open position with exits (TP + SL)
6. Record everything and stream updates to dashboards

---

## 📂 File Map — What to Read (SOURCE OF TRUTH)

### Engine Core (`services/engine/quantsail_engine/`)
> **READ THESE FILES — they are the actual trading logic**

| Path | Purpose |
|------|---------|
| `core/trading_loop.py` | Main orchestrator — the heartbeat of the bot |
| `core/state_machine.py` | Per-symbol state: IDLE→EVAL→ENTRY→IN_POSITION→EXIT |
| `core/entry_pipeline.py` | Entry decision logic (gates, sizing, order creation) |
| `core/exit_pipeline.py` | Exit logic (SL/TP/trailing stop checks) |
| `core/portfolio_risk_manager.py` | Portfolio-level risk constraints |
| `strategies/*.py` | All trading strategies (trend, mean_reversion, breakout, vwap_mean_reversion) |
| `strategies/ensemble.py` | Ensemble combiner — votes, agreement threshold, confidence |
| `strategies/indicators.py` | Pure Python indicators (EMA, RSI, BB, ATR, ADX, MACD, OBV, VWAP, Donchian) |
| `gates/*.py` | All safety gates (profitability, cooldown, daily_lock, regime_filter, streak_sizer, daily_symbol_limit, kill_switch) |
| `breakers/*.py` | Circuit breakers (volatility, spread, consecutive losses, exchange instability) |
| `execution/dry_run_executor.py` | Paper trading executor |
| `execution/live_executor.py` | Real money executor (Binance via ccxt) |
| `execution/binance_adapter.py` | Binance API adapter (ccxt wrapper) |
| `execution/position_sizer.py` | ATR-based position sizing |
| `config/models.py` | Pydantic config models (BotConfig) |
| `config/loader.py` | Config loading (JSON + env vars) |
| `backtest/*.py` | Backtesting engine (executor, runner, metrics, monte_carlo, walk_forward, grid_backtest) |
| `grid/*.py` | Grid trading (grid_config, grid_manager, grid_executor, grid_strategy) |
| `cache/*.py` | Cache layer (news cache, control cache) |
| `alerts/telegram.py` | Telegram alert integration |
| `main.py` | Engine entrypoint |

### API (`services/api/app/`)
> **READ THESE FILES — they connect the engine to the dashboard**

| Path | Purpose |
|------|---------|
| `api/private.py` | All private endpoints (config, bot control, trades, events, users, exchanges) |
| `api/public.py` | Public sanitized endpoints (summary, trades, events, heartbeat) |
| `api/ws.py` | WebSocket streaming (cursor resume, heartbeat, redaction) |
| `api/redact.py` | Event payload redaction for WS |
| `api/errors.py` | Standard error schema |
| `api/grid_data.py` | Grid trading data endpoints |
| `auth/firebase.py` | Firebase JWT verification |
| `auth/dependencies.py` | RBAC dependency injection |
| `db/models.py` | SQLAlchemy ORM models |
| `db/queries.py` | Database query functions |
| `db/events_repo.py` | Event journal repository |
| `public/sanitize.py` | Public response sanitization |
| `public/rate_limit.py` | Redis/in-memory rate limiting |
| `security/encryption.py` | AES-GCM encryption for exchange keys |
| `schemas/config.py` | Config schemas |
| `cache/arming.py` | ARM LIVE flow |
| `cache/news.py` | News pause cache |

### Dashboard (`apps/dashboard/`)
> **READ THESE FILES — this is what the operator sees**

| Path | Purpose |
|------|---------|
| `app/(private)/` or `app/app/` | Private dashboard pages (overview, strategy, risk, events, exchange, users, grid) |
| `app/public/` | Public transparency pages (overview, trades, transparency) |
| `components/dashboard/*.tsx` | All dashboard widgets (equity-chart, kpi-grid, status-banner, recent-trades, breakers-widget, kill-switch-widget, daily-lock-widget, risk-portfolio-widget, strategy-performance-widget, arming-modal, app-shell) |
| `components/public/*.tsx` | Public page components |
| `lib/store.ts` | Zustand state store |
| `lib/api.ts` | API client |
| `lib/ws.ts` | WebSocket client |
| `lib/config.ts` | Dashboard config (mock mode toggle) |
| `lib/utils.ts` | Utility functions |
| `messages/en.json` + `messages/es.json` | i18n strings |
| `types/*.ts` | TypeScript type definitions |

### Configuration & Infrastructure
| Path | Purpose |
|------|---------|
| `infra/docker/docker-compose.yml` | Postgres + Redis Docker setup |
| `services/engine/.env` | Engine env vars (Binance keys, DB, Redis) |
| `services/api/.env` | API env vars (Firebase, DB, Redis, encryption) |
| `apps/dashboard/.env.local` | Dashboard env vars (API URL, Firebase client) |
| `start-all.bat` / `start-all.ps1` | Windows startup scripts |
| `stop-all.bat` | Windows stop script |

---

## 📋 AUDIT SECTIONS — What You Must Investigate & Report

### Section 1: System Identity & Purpose
Answer these questions by reading the code (not just docs):
- What exactly does Quantsail do? What markets does it trade?
- What exchange(s) does it support? How extensible is the adapter pattern?
- What trading strategies are implemented? How do they work?
- What is the ensemble agreement system? Is it configurable?
- Is it a high-frequency bot, swing trader, or something else?
- What is the target user profile? (solo operator, team, public fund?)

### Section 2: Architecture Deep Dive
- Is the separation between Engine, API, and Dashboard clean?
- Are there circular dependencies or tight couplings?
- Is the state machine correct and complete?
- How does data flow from market → strategy → gate → execution → persist → dashboard?
- Is the event system comprehensive? Are there gaps in the event taxonomy?
- Is the config system flexible enough for different market conditions?

### Section 3: Trading Logic & Profitability Audit
> **This is critical. Read every strategy, gate, and execution file.**

- Are the strategies mathematically sound?
- Is the ensemble combiner logic correct and configurable?
- Does the profitability gate actually prevent unprofitable trades?
- Is position sizing correct (ATR-based, risk-per-trade)?
- Are stop-loss and take-profit calculations correct?
- Does the trailing stop work properly?
- Are circuit breakers effective at preventing catastrophic losses?
- Is the daily lock (STOP/OVERDRIVE) logic correct?
- What is the estimated win rate and risk/reward based on the strategy parameters?
- **Can this bot realistically be profitable?** Under what conditions?
- What would you change to improve profitability?

### Section 4: Execution Safety & Live Readiness
- Is the dry-run executor faithful to live behavior?
- Does the live executor handle all edge cases? (partial fills, network errors, rate limits)
- Is the Binance adapter robust? (error handling, reconnection, API changes)
- Is order idempotency actually implemented?
- Is restart reconciliation working? (what happens on crash/restart with open positions?)
- What happens if the exchange goes down mid-trade?
- Are there any race conditions in the trading loop?

### Section 5: Security Audit
- Are exchange API keys stored securely? (AES-GCM encrypted?)
- Is the MASTER_KEY management secure?
- Is Firebase auth properly implemented and verified?
- Are public endpoints truly sanitized? (no secrets leaking)
- Is rate limiting effective?
- Are there any SQL injection, XSS, or CSRF risks?
- Is the `serviceAccountKey.json` in `services/api/` a real key committed to the repo? ⚠️
- Are `.env` files properly gitignored?

### Section 6: 🖥️ Dashboard Completeness Audit (CRITICAL)
> **The operator wants to see EVERYTHING the bot is doing in real-time from the Vercel dashboard, connected to the VPS engine.**

Audit what the dashboard CURRENTLY shows vs. what it SHOULD show. For each item, state: ✅ EXISTS, ⚠️ PARTIAL, or ❌ MISSING.

**Real-Time Bot Activity:**
- [ ] Live bot status (running/stopped/error)
- [ ] Current state per symbol (IDLE/EVAL/ENTRY/IN_POSITION/EXIT)
- [ ] Real-time market data the bot is seeing (price, volume, spread)
- [ ] Strategy signals in real-time (which strategies fired, scores, confidence)
- [ ] Ensemble decision log (what agreed, what didn't, why)
- [ ] Gate decisions in real-time (which gates passed/failed and why)
- [ ] Circuit breaker status (which are active, when they'll expire)
- [ ] Daily PnL lock status (target, current, mode, floor)
- [ ] Open positions with live P&L
- [ ] Order status (pending, filled, canceled)
- [ ] Current equity curve (real-time, not just snapshots)

**Logs & Decision Trail:**
- [ ] Engine log stream (what the bot is doing right now, step by step)
- [ ] Full event log with filtering (by type, level, symbol, time range)
- [ ] Trade reasoning log (why a trade was opened, why it was rejected)
- [ ] Error log (exceptions, API failures, connection issues)
- [ ] Performance metrics (latency, tick processing time, API response time)

**Analytics & Reporting:**
- [ ] Historical trade table with full details (entry/exit prices, PnL, fees, duration)
- [ ] Win rate, Sharpe ratio, max drawdown, profit factor
- [ ] Strategy-level performance breakdown
- [ ] Symbol-level performance breakdown
- [ ] Drawdown chart
- [ ] Risk metrics over time

**Configuration & Control:**
- [ ] Start/stop/pause bot from dashboard
- [ ] ARM LIVE flow (safety confirmation before going live)
- [ ] Edit strategy parameters from dashboard
- [ ] Edit risk parameters from dashboard
- [ ] Manage exchange API keys from dashboard
- [ ] Switch between dry-run and live mode
- [ ] User management (RBAC)

**Infrastructure Monitoring:**
- [ ] VPS health (CPU, memory, disk, network)
- [ ] Database health (connection pool, query latency)
- [ ] Redis health
- [ ] Engine process status (uptime, restarts, crashes)
- [ ] API latency and error rate
- [ ] WebSocket connection status

**What's Missing? Provide a Prioritized Wishlist:**
For every ❌ MISSING item, provide:
1. Why it matters
2. What API endpoint or data source is needed
3. What dashboard component would display it
4. Priority: P0 (must-have for go-live), P1 (should-have), P2 (nice-to-have)

### Section 7: Testing & Coverage Audit
- What is the actual test coverage? Run `pytest --cov` and report numbers.
- Are there integration tests that test real flows end-to-end?
- Are there any untested critical paths?
- Is the backtesting engine validated against known results?
- Are Playwright E2E tests comprehensive?
- Are there load/stress tests?

### Section 8: Deployment & Operations Readiness
- Can this be deployed to a VPS today? What steps are missing?
- Is Docker Compose ready for production? (health checks, restart policies, volumes)
- Is there a deployment pipeline (CI/CD)?
- Is there monitoring/alerting in production?
- What happens if the engine crashes? Is there auto-restart logic?
- Is log rotation configured?
- Is database backup configured?
- How do you update the bot without downtime?

### Section 9: Paper Trading / Testing Readiness
- Can the bot run in dry-run mode end-to-end right now?
- What is needed to start paper trading?
- How do you validate that paper trading results are realistic?
- Is there a way to replay historical data through the bot?
- Can the backtester validate strategy parameters before going live?

---

## 📊 DELIVERABLE FORMAT

Produce your audit report as a single markdown document with the following structure:

```
# Quantsail Full System Audit Report
## Date: [today]
## Auditor: [agent name]

## Executive Summary
- 3-5 sentence overview of findings
- Overall readiness score: [1-10]
- Go/No-Go recommendation for paper trading
- Go/No-Go recommendation for live trading

## 1. System Identity & Purpose
[findings]

## 2. Architecture & Code Quality
### Strengths
### Weaknesses
### Recommendations

## 3. Trading Logic & Profitability
### Strategy Analysis
### Risk Management Analysis
### Profitability Assessment
### Enhancement Recommendations

## 4. Execution Safety
### Findings
### Critical Issues
### Recommendations

## 5. Security Audit
### Findings (with severity: CRITICAL/HIGH/MEDIUM/LOW)
### Recommendations

## 6. Dashboard Completeness Audit
### Current Coverage Matrix (✅/⚠️/❌ for each item)
### Missing Features (prioritized P0/P1/P2)
### Recommendations with Implementation Details

## 7. Testing & Coverage
### Coverage Report
### Gap Analysis
### Recommendations

## 8. Deployment Readiness
### VPS Deployment Checklist
### Missing Infrastructure
### Recommendations

## 9. Paper Trading Readiness
### Checklist
### What's Needed
### Recommended Test Plan

## 10. Full Pros & Cons Summary
### ✅ Strengths (what's done well)
### ❌ Weaknesses (what needs work)
### ⚠️ Risks (what could go wrong)

## 11. Prioritized Action Plan
### P0 — Must Fix Before Any Trading
### P1 — Should Fix Before Live Trading
### P2 — Nice to Have for Production
### P3 — Future Enhancements
```

---

## ⚙️ RULES FOR THE AUDITOR

1. **Code is the source of truth.** Read the actual `.py` and `.tsx` files, not just docs. Docs may be aspirational or outdated.
2. **Be brutally honest.** The owner wants to know exactly what's wrong and what's right. No sugar-coating.
3. **Be specific.** Don't say "the security could be better" — say "the `serviceAccountKey.json` at `services/api/serviceAccountKey.json` appears to be a real Firebase service account key committed to the repository. This is a CRITICAL security violation."
4. **Give actionable recommendations.** For every problem, suggest a concrete fix with file paths.
5. **Test what you can.** Run linting, type checking, and tests where possible and report actual results.
6. **Think like a trader.** Would YOU trust your money to this bot? Why or why not?
7. **Think like a DevOps engineer.** Can this run 24/7 on a VPS without manual intervention?
8. **Think like a security researcher.** What could an attacker exploit?
9. **Don't skip the dashboard audit.** The operator explicitly wants to see EVERYTHING the bot does from the dashboard — every decision, every log, every signal. Audit what's missing thoroughly.
10. **No privacy leaks.** Note anywhere that private data (API keys, secrets, internal IDs) could be exposed through the public dashboard or API.

---

## 🗂️ DOCS TO CROSS-REFERENCE (but verify against code)

| Doc | Location |
|-----|----------|
| System Overview | `docs/00_SYSTEM_OVERVIEW.md` |
| PRD | `docs/01_PRD.md` |
| Architecture | `docs/02_ARCHITECTURE.md` |
| API Spec | `docs/03_API_SPEC.md` |
| DB Schema | `docs/04_DB_SCHEMA.md` |
| UI Spec | `docs/05_UI_SPEC.md` |
| Security/Ops | `docs/06_SECURITY_OPS.md` |
| Validation | `docs/07_VALIDATION_AND_GO_LIVE.md` |
| Config Spec | `docs/09_CONFIG_SPEC.md` |
| Features | `docs/10_FEATURES.md` + `FEATURES.md` |
| Folder Structure | `docs/11_FOLDER_STRUCTURE_DETAILED.md` |
| Engine Spec | `docs/13_ENGINE_SPEC.md` |
| Event Taxonomy | `docs/14_EVENT_TAXONOMY.md` |
| Observability | `docs/15_OBSERVABILITY.md` |
| Security Threat Model | `docs/16_SECURITY_THREAT_MODEL.md` |
| UI Wireframes | `docs/17_UI_WIREFRAMES_TEXT.md` |
| Environment Setup | `docs/19_ENVIRONMENT_SETUP.md` |
| Complete Impl Guide | `docs/QUANTSAIL_COMPLETE_IMPLEMENTATION_GUIDE.md` |
| Quick Reference | `docs/QUICK_REFERENCE_GUIDE.md` |
| Changelog | `docs/CHANGELOG.md` |
| Master Checklist | `todo.md` |
| Setup Guide | `SETUP_GUIDE.md` |

---

## ⏱️ ESTIMATED EFFORT

This is a large codebase (~190 source files across 3 services). Budget accordingly:
- **Engine**: ~96 Python files (heaviest — all trading logic)
- **API**: ~26 Python files
- **Dashboard**: ~68 TypeScript/TSX files
- **Docs**: ~25 spec files

Take your time. Be thorough. The owner is investing real money based on this audit.
