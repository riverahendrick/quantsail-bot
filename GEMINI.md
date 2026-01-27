# Quantsail — Crypto Spot Auto-Trading Bot

## Project Overview
Quantsail is an automated crypto spot trading system designed for safety, profitability, and transparency. It features a private operator dashboard for control and a public transparency dashboard for sanitized reporting.

**Key Components:**
- **Engine (Python):** Handles strategies, gating, execution, and persistence.
- **API (FastAPI):** Manages authentication, configuration, and data streaming.
- **Database:** Postgres (System of Record) and Redis (Cache).
- **Frontend (Next.js):** Private Operator Dashboard and Public Transparency Dashboard.

**Deployment Architecture:**
- **VPS:** Hosts the Engine, API, Postgres, and Redis.
- **Vercel:** Hosts the Frontend UI (no secrets stored here).

## Current Status
The project is currently in the **Documentation & Planning Phase**. The repository contains detailed specifications, architecture designs, and a prompt-driven implementation plan. No source code has been generated yet.

## Getting Started
The implementation follows a strict, prompt-driven workflow defined in `docs/08_PROMPTS/`.

1.  **Read the Basics:**
    - `README.md` (Project entry point)
    - `GLOBAL_RULES.md` (Mandatory AI rules)
    - `docs/00_SYSTEM_OVERVIEW.md` (High-level understanding)
    - `docs/01_PRD.md` (Detailed requirements)

2.  **Implementation Workflow:**
    - Execute the prompts in `docs/08_PROMPTS/` sequentially.
    - Each prompt corresponds to a specific milestone in `todo.md`.
    - **Do not skip steps.** Follow the `todo.md` checklist rigorously.

## Development Mandates
**Strict adherence to `GLOBAL_RULES.md` is required.**

- **Test-Driven Development (TDD):** Write tests *before* implementation.
- **100% Code Coverage:** Mandatory for all touched files.
- **Internationalization (i18n):** Support English (EN) and Spanish (ES) for all UI strings from day one.
- **Security First:**
    - Secrets must be encrypted at rest.
    - No secrets in logs, events, or public endpoints.
    - strict RBAC for private endpoints.
- **No Guesswork:** Implement exactly what is specified in the docs. If ambiguous, ask.

## Directory Structure
- `docs/`: Comprehensive project documentation.
    - `08_PROMPTS/`: Ordered prompts for building the system.
- `GLOBAL_RULES.md`: Universal rules for AI agents working on this project.
- `README.md`: Project summary and reading order.
- `todo.md`: Master checklist for tracking progress.

## Key Commands (Future)
*Commands will be added here once the project scaffolding (M0) is complete.*

- **Dashboard:** `npm run dev` (likely)
- **API/Engine:** `docker-compose up` (likely)
