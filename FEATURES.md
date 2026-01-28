# FEATURES - Quantsail Feature Registry

_Last updated: 2026-01-28_

## User Features
- [x] Dashboard i18n (EN/ES) with locale switch
- [x] Public overview page at /public/overview
- [x] Public trades and transparency pages

## Admin Features
- [x] Operator dashboard (private)
- [x] Admin RBAC and configuration controls
- [x] User management (owner-only)

## Developer Features
- [x] Lint/typecheck/test guardrails (dashboard + services)
- [x] Database migrations via Alembic

## Backend Features
- [x] API health endpoint (/v1/health)
- [x] Private API auth (Firebase JWT) + RBAC enforcement
- [x] Public API endpoints with sanitization + rate limiting
- [x] Private WS event stream with cursor resume + redaction
- [x] Engine placeholder entrypoint
- [x] Postgres schema + migrations applied
- [x] API DB health check (/v1/health/db)
