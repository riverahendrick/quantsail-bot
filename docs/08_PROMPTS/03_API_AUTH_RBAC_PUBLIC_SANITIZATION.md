# Prompt 03 — API auth/RBAC + strict public sanitization router

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
We need two completely different trust zones: private operator APIs (JWT+RBAC) and public transparency APIs (sanitized). Any leakage destroys the product.

## Goal (this prompt only)
Implement Firebase JWT verification, RBAC middleware, private endpoints, AND a separate public router that only returns sanitized payloads (plus tests proving sanitization).

## Scope boundaries (do NOT go beyond this)
- Do not build dashboards yet beyond what’s needed for tests.
- Do not implement live trading.
- Do not add endpoints not listed in docs/03_API_SPEC.md unless docs updated first.

## Files to touch (allowed edits/creates)
- services/api/**
- todo.md
- docs/CHANGELOG.md
- docs/03_API_SPEC.md (ONLY if missing details must be clarified first)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- (optional) docs/03_API_SPEC.md if you clarified missing details

## Deliverables (must exist at end)
- Firebase JWT verification in API.
- RBAC enforcement per endpoint.
- Public router `/public/v1/*` that serves only sanitized trade/event/summary payloads.
- Unit tests for RBAC and sanitization.
- Basic rate limiting on public endpoints.

## Implementation steps (do in order; be explicit)
1) Read docs/03_API_SPEC.md and PRD sections 4.8 (transparency) and security sections.
2) Implement auth layer:
   - Verify Firebase JWT for private routes.
   - Extract firebase_uid and map to local user role (users table).
3) Implement RBAC middleware/decorator:
   - Each private endpoint declares allowed roles.
   - Unauthorized must return 403 with standard error schema.
4) Implement private endpoints minimal set (MVP):
   - /v1/health, /v1/status
   - /v1/trades, /v1/events, /v1/equity (auth required)
5) Implement public router:
   - /public/v1/summary, /public/v1/trades, /public/v1/events, /public/v1/heartbeat
   - Enforce sanitization rules:
     * never include exchange_order_id
     * never include raw payload fields that can leak secrets
     * optionally bucket sizes if configured
     * only include events with public_safe=true
6) Implement rate limiting for public endpoints (Redis-based preferred; fallback in-memory for dev).
7) Tests (must prove safety):
   - private endpoints blocked without auth
   - RBAC enforced for different roles
   - public endpoints never contain forbidden fields (explicit assertions)
   - public events endpoint returns only public_safe=true rows
8) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- API lint/typecheck: `uv -C services/api run ruff check .` and `uv -C services/api run mypy .`
- API tests: `uv -C services/api run pytest -q --cov`
- If Redis is used for rate limiting: run infra docker compose and include an integration test or a mocked redis client test.


## Acceptance checklist (must check all)
- [x] Private endpoints require valid JWT
- [x] RBAC blocks forbidden roles (403)
- [x] Public endpoints are sanitized (tests assert forbidden fields absent)
- [x] Public events only return public_safe=true
- [x] Rate limiting exists on public endpoints
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated

