# Prompt 01 — Guardrails: lint/typecheck/tests + i18n EN/ES enforcement

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
Your project will be built incrementally by AI agents. Without strong guardrails, quality degrades, strings get hardcoded, and behavior drifts from the docs.

## Goal (this prompt only)
Add enforceable quality gates: lint/typecheck/test commands, Playwright baseline E2E, and i18n EN/ES with an automated guard that blocks hardcoded UI strings.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement trading features.
- Do NOT build full dashboard UI yet (only minimal public page needed for the i18n + E2E baseline).

## Files to touch (allowed edits/creates)
- apps/dashboard/**
- tests/e2e/** (or apps/dashboard/playwright/** depending on structure)
- services/api/** (tooling config)
- services/engine/** (tooling config)
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Dashboard: i18n EN/ES installed and wired.
- Dashboard: `/public/overview` exists with translated UI.
- Dashboard: Playwright baseline E2E test covers `/public/overview`.
- A guard (lint rule or test) fails if hardcoded strings are introduced outside the i18n system.
- Python: ruff + mypy + pytest + coverage set up in both services.

## Implementation steps (do in order; be explicit)
1) Dashboard tooling:
   - Add typecheck script (tsc) if missing.
   - Add lint script (eslint) if missing.
   - Add test script (vitest/jest optional; can be skipped if not needed yet).
2) i18n EN/ES (mandatory):
   - Implement translation files (EN + ES) and a locale switch mechanism.
   - Create `/public/overview` with ONLY translated strings.
   - Add an automated guard:
     Option A: eslint rule/lint script that bans raw string literals in React components (allowlist exceptions: className, testIDs, etc).
     Option B: a test that scans source files and fails if non-allowed string patterns appear.
   - Document how to add new translations.
3) Playwright baseline E2E:
   - Add a test that loads `/public/overview`.
   - Assert English text appears by default and Spanish appears when locale set.
4) Python guardrails:
   - Add ruff config and mypy config.
   - Add pytest + coverage config enforcing 100% for touched files.
5) Update docs:
   - Update README “Developer Commands” section if required.
   - Update todo.md and CHANGELOG.


## Tests to run and report (exact commands)
- Dashboard: `pnpm -C apps/dashboard lint`
- Dashboard: `pnpm -C apps/dashboard typecheck`
- E2E: `pnpm -C apps/dashboard exec playwright test`
- API: `uv -C services/api run ruff check .` and `uv -C services/api run mypy .` and `uv -C services/api run pytest --cov`
- Engine: `uv -C services/engine run ruff check .` and `uv -C services/engine run mypy .` and `uv -C services/engine run pytest --cov`


## Acceptance checklist (must check all)
- [x] i18n EN/ES works and is used on `/public/overview`
- [x] Hardcoded UI strings are blocked by automated check (proof: intentionally failing example documented or test demonstrates)
- [x] Playwright baseline passes
- [x] Ruff + mypy + pytest pass in API and Engine
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated
