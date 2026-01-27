# Quantsail — Master Checklist

> Every prompt must add a section here and check it off when complete.

## Project milestones
### M0 — Repo bootstrapped
- [ ] Next.js dashboard scaffolded in `apps/dashboard` (no nested root)
- [ ] FastAPI scaffolded in `services/api`
- [ ] Engine scaffolded in `services/engine`
- [ ] Postgres + Redis via `infra/docker/docker-compose.yml`
- [ ] Baseline lint/typecheck/test commands working

### M1 — Data + audit trail
- [ ] Postgres schema migrated (Alembic)
- [ ] Event taxonomy implemented end‑to‑end
- [ ] WS streaming functional (private)

### M2 — Trading logic (dry‑run)
- [ ] Strategy outputs + ensemble gating implemented
- [ ] Fee+slippage profitability gate implemented
- [ ] Risk sizing + exits implemented
- [ ] Circuit breakers + daily lock implemented
- [ ] Dry‑run trades and equity snapshots persisted

### M3 — Dashboards
- [ ] Private operator dashboard functional
- [ ] Public transparency dashboard functional and sanitized
- [ ] E2E tests for critical pages

### M4 — Live (later)
- [ ] ARM LIVE flow implemented
- [ ] Binance spot live execution (idempotent) + reconciliation
