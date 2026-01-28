# Quantsail — Crypto Spot Auto‑Trading + Live Transparency Dashboard

This repository is designed to be built by AI coding agents **without guesswork**.
The docs define exact behavior, interfaces, and acceptance criteria.

## Non‑negotiables
- Read `GLOBAL_RULES.md` first and comply.
- Do **not** create a nested root folder.
- TDD everywhere; **100% coverage for touched files**; E2E for critical flows.
- i18n (EN/ES) from day one (no hardcoded UI strings).
- Vercel hosts UI only (no secrets). VPS hosts engine+API+DB.

## Reading order
1. `docs/00_SYSTEM_OVERVIEW.md`
2. `docs/01_PRD.md`
3. `docs/02_ARCHITECTURE.md`
4. `docs/09_CONFIG_SPEC.md`
5. `docs/13_ENGINE_SPEC.md`
6. `docs/03_API_SPEC.md`
7. `docs/04_DB_SCHEMA.md`
8. `docs/05_UI_SPEC.md`
9. `docs/08_PROMPTS/` (execute in order)

9) docs/06_SECURITY_OPS.md
10) docs/07_VALIDATION_AND_GO_LIVE.md
11) docs/12_GLOSSARY.md

## Developer Commands
### Infrastructure
- `cd infra/docker && docker compose up -d`
- `cd infra/docker && docker compose down`
- Postgres: localhost:5433 (container 5432), Redis: localhost:6380 (container 6379)

### Dashboard (Next.js)
- `cd apps/dashboard && pnpm install`
- `cd apps/dashboard && pnpm dev` (http://localhost:3000)
- `cd apps/dashboard && pnpm lint`
- `cd apps/dashboard && pnpm typecheck`

### API (FastAPI)
- Set `DATABASE_URL=postgresql+psycopg://quantsail:postgres@localhost:5433/quantsail`
- Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-service-account.json`
- Optional: `REDIS_URL=redis://localhost:6380/0` (public rate limiting)
- `cd services/api && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- Health check: http://127.0.0.1:8000/v1/health
- DB health check: http://127.0.0.1:8000/v1/health/db
- `cd services/api && uv run alembic upgrade head`
- `cd services/api && uv run pytest -q --cov`

### Engine
- `cd services/engine && uv run python -m quantsail_engine.main`
- `cd services/engine && uv run pytest -q --cov`
