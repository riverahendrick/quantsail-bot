# Prompt 00 — Setup (scaffold generators; NO hand‑creating boilerplate)

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
We must initialize the repo with official generators so dependencies and configs are correct. Many agents mistakenly create files manually or create a nested folder; this prompt prevents that.

## Goal (this prompt only)
From the EXISTING repo root, generate a blank Next.js app under `apps/dashboard` and initialize Python services under `services/api` and `services/engine` using `uv`, plus docker‑compose for Postgres+Redis. Everything must run locally.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement trading logic.
- Do NOT add extra UI pages beyond a hello/health check.
- Do NOT create a nested repo root folder.
- Do NOT scaffold by writing every file manually; use official generators.

## Files to touch (allowed edits/creates)
- apps/dashboard/**
- services/api/**
- services/engine/**
- infra/docker/docker-compose.yml
- infra/scripts/**
- README.md (only the commands section)
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- `apps/dashboard/` runs `pnpm dev` successfully.
- `services/api/` runs FastAPI and serves `/v1/health`.
- `services/engine/` is importable and has a minimal runnable entrypoint.
- `infra/docker/docker-compose.yml` starts Postgres and Redis.
- Root docs updated with exact run commands.

## Implementation steps (do in order; be explicit)
1) Verify current folder is repo root:
   - It must contain `GLOBAL_RULES.md` and `docs/`.
   - If you accidentally created a nested folder previously, STOP and fix by moving generated files up and deleting the nested folder.
2) Dashboard scaffold (official generator):
   - Run the official Next.js generator to create a NEW app in `apps/dashboard`.
   - Select TypeScript, ESLint, App Router, and Tailwind if desired (Tailwind is allowed; do not over-style now).
   - Use pnpm for dependency management.
3) API scaffold (uv + FastAPI):
   - Initialize a uv project in `services/api`.
   - Create `app/main.py` with FastAPI instance.
   - Implement GET `/v1/health` returning `{ "ok": true }`.
   - Add 1 unit test that calls the app with TestClient and asserts response.
4) Engine scaffold (uv + package):
   - Initialize a uv project in `services/engine`.
   - Create a package `quantsail_engine/` with `__init__.py`.
   - Add `quantsail_engine/main.py` with a placeholder `main()` that logs “engine boot” and exits 0.
   - Add 1 unit test that imports the package and calls `main()`.
5) Infrastructure:
   - Create `infra/docker/docker-compose.yml` with Postgres + Redis.
   - Use volumes for persistence; expose ports only as needed for local dev.
   - Provide basic env placeholders (no secrets committed).
6) Convenience scripts:
   - `infra/scripts/start_infra.sh` to start docker compose.
   - `infra/scripts/stop_infra.sh` to stop.
   - `infra/scripts/test_all.sh` that runs dashboard lint/typecheck, api tests, engine tests.
7) Smoke test (must be performed):
   - Start infra; run API; run dashboard; import engine.
8) Documentation updates:
   - Update README with exact commands and expected URLs.
   - Update `todo.md` and `docs/CHANGELOG.md`.


## Tests to run and report (exact commands)
- Infra: `cd infra/docker && docker compose up -d`
- API: `cd services/api && uv run pytest -q --cov`
- Engine: `cd services/engine && uv run pytest -q --cov`
- Dashboard: `cd apps/dashboard && pnpm install && pnpm lint && pnpm dev`


## Acceptance checklist (must check all)
- [ ] No nested repo root folder exists
- [ ] `docker compose up -d` starts Postgres and Redis
- [ ] API responds at `/v1/health`
- [ ] Engine imports and placeholder runs
- [ ] Dashboard boots in dev mode
- [ ] Tests pass with 100% coverage for touched files
- [ ] todo.md + CHANGELOG updated

