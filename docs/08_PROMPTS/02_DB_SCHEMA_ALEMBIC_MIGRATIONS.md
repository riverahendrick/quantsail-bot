# Prompt 02 — Postgres schema + Alembic migrations + schema verification tests

## Mandatory first step (before anything else)
1) Open and read `GLOBAL_RULES.md` in the repo root.
2) Confirm you will follow EVERY rule in it (do not paste the rules).
3) Confirm you will NOT create a nested repo root folder (no repo-inside-repo).
4) Use all available tooling and MCPs (linters, typecheckers, tests, formatting, search, best‑practice research when needed).

## No‑guessing rule (critical)
If anything is unclear:
- First, search for the answer in `docs/`.
- If missing, **update the relevant spec doc** (PRD/spec) BEFORE implementing code.
- Do NOT invent behavior, defaults, UI content, or security rules.

## End‑of‑task updates (mandatory)
- Update `todo.md` (add a section for this prompt and check items).
- Update `docs/CHANGELOG.md` (what changed + why).
- Update `docs/10_FEATURES.md` ONLY if feature scope changes.

## Testing policy (non‑negotiable)
- TDD required.
- 100% coverage for all touched files.
- Run unit tests + integration tests (when touching DB/API/engine integration) + E2E tests (when touching UI routes).
- Provide exact commands run and copy/paste outputs.

## Required final report format (must be included)
1) Files changed (bulleted)
2) Commands run (bulleted)
3) Test results (paste outputs)
4) Checklist updates (todo.md + docs)
5) Notes / follow‑ups (optional)


## Context (why this exists)
Postgres is the system-of-record. We cannot allow schema drift or implicit columns. This prompt makes DB explicit and test-verified.

## Goal (this prompt only)
Implement the DB schema required by the docs, create Alembic migrations, and add an integration test that applies migrations and verifies tables/columns/indexes exist.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement trading engine logic yet.
- Do NOT implement UI.
- Do NOT add columns not specified by docs unless you first update docs/04_DB_SCHEMA.md.

## Files to touch (allowed edits/creates)
- services/api/**
- infra/docker/docker-compose.yml (only if needed)
- todo.md
- docs/CHANGELOG.md
- docs/04_DB_SCHEMA.md (ONLY if you must clarify missing fields before coding)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- (optional) docs/04_DB_SCHEMA.md if it was incomplete

## Deliverables (must exist at end)
- SQLAlchemy models for the required tables.
- Alembic migrations.
- Integration test that verifies schema correctness after migration.
- API can connect to DB (smoke check).

## Implementation steps (do in order; be explicit)
1) Read the explicit DB requirements in docs/04_DB_SCHEMA.md (and PRD persistence sections).
2) Implement SQLAlchemy models matching docs exactly.
3) Configure Alembic:
   - ensure migrations are deterministic and reproducible.
4) Create a migration and apply it.
5) Write an integration test:
   - starts Postgres (docker compose),
   - runs `alembic upgrade head`,
   - queries information_schema and pg_indexes to verify:
     * each required table exists,
     * required columns exist with correct types,
     * required indexes/constraints exist.
6) Add a smoke endpoint or internal check to prove API DB connection works (no auth required yet).
7) Update todo.md and CHANGELOG with what was added and how to run migrations.


## Tests to run and report (exact commands)
- Infra: `cd infra/docker && docker compose up -d`
- Migrations: `cd services/api && uv run alembic upgrade head`
- Tests: `cd services/api && uv run pytest -q --cov`


## Acceptance checklist (must check all)
- [x] Alembic upgrade head succeeds on fresh DB
- [x] Schema verification integration test passes
- [x] No undocumented columns were introduced (unless docs updated first)
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated

