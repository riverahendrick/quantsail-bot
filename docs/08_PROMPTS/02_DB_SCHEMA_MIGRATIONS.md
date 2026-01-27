# Prompt 02 — Postgres schema + Alembic migrations + schema verification tests

## Mandatory first steps (before anything else)
1) Open and read `GLOBAL_RULES.md` (repo root).
2) Confirm you will follow every rule (do not paste rules).
3) Confirm you will not create a nested repo root folder.
4) Use all available tools/skills/MCPs available in your environment and do best-practice research when needed.

## No‑guessing rule
- If anything is unclear, search `docs/` first.
- If still unclear, **update the relevant doc** before coding.
- Do not invent behavior or “assume” defaults beyond docs.

## End‑of‑prompt obligations
- Update `todo.md` (add a section for this prompt and check items).
- Update `docs/CHANGELOG.md` (what changed + why).
- Update `docs/10_FEATURES.md` only if scope changes.

## Testing policy
- TDD required.
- 100% coverage for all touched files.
- Run unit + integration + E2E (if relevant).
- Report exact commands and outputs.

## Final report format (must be included)
1) Files changed (bulleted)
2) Commands run (bulleted)
3) Test results (paste outputs)
4) Checklist updates (what was checked in todo.md + docs)
5) Notes / follow-ups (optional)


## Context (what we’re building)
Postgres is the source-of-truth for trades/orders/events/config. We need migrations and tests to prevent drift.

## Goal (this prompt only)
Implement DB schema tables and Alembic migrations, plus an integration test that verifies required tables/columns exist after migration.

## Non‑goals (explicitly do NOT do these)
- Do not implement trading logic.
- Do not implement dashboard pages.
- Do not add unapproved columns beyond docs.

## Deliverables (must exist at end)
- SQLAlchemy models for required tables.
- Alembic migrations.
- Integration test: apply migrations against a test DB and assert schema matches requirements.
- API can connect to DB and run a simple query.

## Implementation steps (do in order)
1) Read docs/04_DB_SCHEMA.md and PRD sections that mention persistence.
2) Implement SQLAlchemy models in services/api.
3) Configure Alembic.
4) Generate and apply migration.
5) Add integration test that:
   - spins up Postgres (docker) or uses test container,
   - runs alembic upgrade head,
   - queries information_schema for tables/columns and asserts existence.


## Tests to run and report
- `docker compose -f infra/docker/docker-compose.yml up -d`
- `uv -C services/api run alembic upgrade head`
- `uv -C services/api run pytest --cov`


## Definition of Done (check all)
- [ ] Migrations apply cleanly
- [ ] Schema verification integration test passes
- [ ] No extra columns beyond docs (unless docs updated first)
- [ ] `todo.md` and `docs/CHANGELOG.md` updated
