# Quantsail — Folder Structure (Detailed Guide)

This guide is written for someone who does not know software engineering. It explains what goes where, and why.

## Golden rule: the repo root is THIS folder
Never create a new project folder inside the repo root. The root is where you see:
- `GLOBAL_RULES.md`
- `README.md`
- `docs/`

If a generator accidentally created a nested folder (example `quantsail/` inside the repo), you must:
1) Move files to the correct paths below
2) Delete the nested folder
3) Update `docs/CHANGELOG.md`

## The full layout (what each folder means)

### 1) docs/
Human-readable documents and plans.
- PRD: what the product must do
- Architecture: how we organize code and services
- Specs: API, DB, UI, security
- Prompts: step-by-step build tasks for AI agents
- Changelog: a log of what changed

You should update docs whenever behavior changes, because docs are the contract.

### 2) apps/dashboard/
The web user interface (Next.js).
- Private pages: operator console (requires login)
- Public pages: transparency dashboard (no login)
This is deployed to Vercel.
Important: the dashboard must never contain exchange secrets.

### 3) services/api/
The backend API (FastAPI).
- Auth + RBAC
- Stores encrypted exchange keys in DB
- Serves private endpoints to the dashboard
- Serves public sanitized endpoints to the public dashboard
- Streams events over WebSocket

Runs on the VPS.

### 4) services/engine/
The trading brain (Python).
- Reads market data
- Runs strategies
- Applies risk and gating
- Simulates trades in dry-run
- Places orders in live mode (later)
- Records trades and emits events

Runs on the VPS.

### 5) packages/shared/
Shared types and schemas that both API and dashboard can use.
Example:
- shared API types
- config schemas
- event payload schemas

This avoids mismatches between backend and frontend.

### 6) infra/docker/
Infrastructure configuration.
- `docker-compose.yml` for Postgres + Redis
- optional Dockerfiles
This makes local and VPS setup consistent.

### 7) infra/scripts/
Operational scripts.
Examples:
- database migration script
- backup script
- deploy script
These scripts should be simple and safe.

### 8) tests/e2e/
End-to-end tests.
- Playwright tests that run the dashboard and validate key flows
E2E tests catch issues unit tests don’t.

## “Files you must update” habit
Whenever you change code, you also update:
- `todo.md` (checklist)
- `docs/CHANGELOG.md` (what changed + why)
- `docs/10_FEATURES.md` (feature registry, if feature scope changed)

---

## Exact folder layout (must match)

# Quantsail — Folder Structure (Exact)

Repo root (this folder):
- GLOBAL_RULES.md
- README.md
- todo.md
- docs/
- apps/
- services/
- packages/
- infra/
- tests/

apps/
- dashboard/                 # Next.js app (Vercel)
  - src/
  - public/
  - tests/                   # UI unit tests (optional)

services/
- api/                       # FastAPI service (VPS)
  - app/
  - tests/
  - alembic/
- engine/                    # Trading engine (VPS)
  - quantsail_engine/
  - tests/

packages/
- shared/                    # Shared types/schemas (e.g., Pydantic models)

infra/
- docker/
  - docker-compose.yml
- scripts/
  - run_all.sh
  - migrate.sh
  - seed_dev.sh

tests/
- e2e/                       # Playwright tests
