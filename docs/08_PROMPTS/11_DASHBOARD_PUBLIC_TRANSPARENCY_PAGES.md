# Prompt 11 — Public transparency dashboard (sanitized)

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
Public dashboard builds trust. It must show what the bot is doing without exposing sensitive execution or identity details.

## Goal (this prompt only)
Implement `/public/overview`, `/public/trades`, and `/public/transparency` using ONLY public endpoints. Enforce sanitization and add E2E tests.

## Scope boundaries (do NOT go beyond this)
- Do NOT include any private data.
- Do NOT use private endpoints.
- Do NOT add user auth requirements for public pages.

## Files to touch (allowed edits/creates)
- apps/dashboard/**
- tests/e2e/**
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Public pages implemented with i18n.
- Uses `/public/v1/*` endpoints only.
- Displays equity curve, metrics, sanitized trade feed, and explanation page.
- E2E tests verifying pages load and show sanitized content.

## Implementation steps (do in order; be explicit)
1) Implement `/public/overview`:
   - Status banner
   - KPI cards (equity, pnl today, win rate, profit factor) using public summary
   - Equity curve chart (if endpoint supports; otherwise show placeholder with TODO and update API spec/docs before coding)
2) Implement `/public/trades`:
   - Sanitized trades table (no exchange IDs, optional size buckets, optional delay)
   - Filters by symbol
3) Implement `/public/transparency`:
   - Explain pipeline: strategies → ensemble → gates → breakers → daily lock
   - Explicitly list what is hidden (keys, account identity, order IDs, exact sizes if configured)
4) Ensure all text is i18n-driven.
5) Add E2E tests for each page.
6) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Dashboard: `pnpm -C apps/dashboard lint`
- Dashboard: `pnpm -C apps/dashboard typecheck`
- E2E: `pnpm -C apps/dashboard exec playwright test`


## Acceptance checklist (must check all)
- [ ] Public pages call ONLY /public endpoints
- [ ] Sanitization is preserved in UI (no forbidden fields can appear)
- [ ] E2E tests pass
- [ ] todo.md + CHANGELOG updated

