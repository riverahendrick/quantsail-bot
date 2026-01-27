# Repository Guidelines

This repo is doc-driven. Read `GLOBAL_RULES.md` and the specs in `docs/` (start with `docs/00_SYSTEM_OVERVIEW.md`) before coding, and never create a nested repo root. When code changes, update `todo.md` and `docs/CHANGELOG.md`; update `docs/10_FEATURES.md` when feature scope changes.

## Project Structure & Module Organization
- `docs/` holds the PRD, architecture, API/DB/UI specs, prompts, and the changelog.
- `apps/dashboard/` is the Next.js dashboard (private operator UI and public transparency pages).
- `services/api/` is the FastAPI backend; `services/engine/` is the Python trading engine.
- `packages/shared/` stores shared schemas and types.
- `infra/docker/` and `infra/scripts/` contain local/VPS infrastructure assets.
- `tests/e2e/` contains Playwright end-to-end tests.

## Build, Test, and Development Commands
- `pnpm -C apps/dashboard dev` Start the dashboard locally.
- `pnpm -C apps/dashboard lint` Run dashboard linting.
- `pnpm -C apps/dashboard typecheck` Run dashboard TypeScript checks.
- `pnpm -C apps/dashboard exec playwright test` Run dashboard E2E tests.
- `uv -C services/api run ruff check .` and `uv -C services/api run mypy .` Lint and type-check the API.
- `uv -C services/api run pytest -q --cov` Run API tests with coverage.
- `uv -C services/engine run ruff check .` and `uv -C services/engine run mypy .` Lint and type-check the engine.
- `uv -C services/engine run pytest -q --cov` Run engine tests with coverage.

## Coding Style & Naming Conventions
Follow the existing lint and type-check tooling (ESLint/TypeScript in the dashboard, ruff/mypy in Python). Use descriptive, domain-specific names and avoid generic names like `data`. All user-facing UI text must be internationalized (EN/ES) and must not be hardcoded in components.

## Testing Guidelines
TDD is required with 100% coverage for touched files. Keep tests in `services/*/tests/` or `tests/e2e/` and mirror the app structure. Run unit tests plus E2E tests for UI routes you change.

## Commit & Pull Request Guidelines
This checkout has no Git history, so use concise, imperative commit subjects (example: "Add risk gate checks") and include a scope if it clarifies intent. PRs should describe changes, link issues, list tests run, and include screenshots for UI changes.

## Security & Configuration Tips
The dashboard is deployed to Vercel and must not contain secrets. Engine, API, Postgres, and Redis run on the VPS. Follow `docs/09_CONFIG_SPEC.md` for configuration and keep sensitive values in environment variables only.
