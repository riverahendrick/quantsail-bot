# 🌐 MASTER GLOBAL RULES FOR AI DEV AGENTS (Universal)

> **Purpose:** A single, universal rulebook to guide AI-assisted development across *any* stack or domain.
> **Scope:** Applies to Web, Mobile, Backend/API, SaaS, Crypto/Web3, and Infra — using **tags** to determine what’s relevant.
> **Core promise:** No regressions. No duplicate implementations. No mock leaks. No silent security risk. Production-ready by default.

---

## 🚨 CRITICAL GATES (READ FIRST — BEFORE WRITING ANY CODE)

These are **priority rules**. If you violate any of these, stop and fix the approach before coding.

### 1) Repo Intelligence & Non‑Duplication Gate `[ALL][EXISTING-REPO]`
- **Search first. Build second.** Before implementing anything, scan the repo to confirm whether the feature, file, module, or pattern already exists.
- **Never create duplicates** (folders, components, utilities, services) if an existing one can be extended or reused.
- **Never truncate/overwrite** existing files without explicit permission. Make incremental, reversible changes.
- If adding something “new”, you must state where you looked (files/paths) and why an existing solution was not sufficient.

### 2) Mock‑Leak Prevention Gate `[ALL]`
- **Never ship mock/stub behavior to production paths.**
- Mocks are allowed **only** in tests/dev/storybook behind explicit toggles and **hard guards**:
  - **Env gating**: `NODE_ENV !== 'production'` AND `ENABLE_MOCKS === 'true'`
  - **Dynamic import** of mock tooling so it is not bundled into prod builds when possible.
  - **CI guard**: run a production build with prod env and fail if mocks are enabled or imported outside allowed locations.
  - **Lint guard**: forbid imports from `/mocks/` outside `*.test.*`, `*.spec.*`, `*.stories.*`, and `e2e/**`.
  - **Runtime guard**: if `NODE_ENV=production && ENABLE_MOCKS=true`, crash loudly with a clear message.

### 3) CI / Verification Gate `[ALL]`
- **No code is “done” until verified.** Minimum verification includes:
  - lint + typecheck
  - unit + integration tests (and E2E where relevant)
  - coverage report
  - build (and deploy preview if available)
- If CI doesn’t exist yet, create the **minimal pipeline** (`lint → typecheck → test → coverage → build`) and document it.

### 4) Coverage Gate `[ALL]`
- **Follow the repo’s configured thresholds** if they exist (do not invent new numbers).
- If the repo has *no* thresholds, set a safe default and document it (see Coverage Policy section).
- **Default policy (unless repo overrides):**
  - **Touched meaningful files:** aim for **100%** (statements/branches/lines/functions).
  - **Repo-wide gate:** high but pragmatic (e.g., ≥90% overall), with explicit allowlisted exclusions (generated/types-only/barrel files).

### 5) API Contract Gate `[API][BACKEND][WEB]`
- If you add/change an API, you must maintain a machine-readable contract:
  - REST: OpenAPI
  - GraphQL: GraphQL schema
  - gRPC: Protobuf
  - Events/Webhooks: JSON Schema (or equivalent)
- Contract breaking changes must be detected by CI (schema diff / contract tests).

### 6) Security Baseline Gate `[ALL]`
- Never commit secrets (keys/tokens/passwords). Use env vars + secret managers.
- All auth/authz must be enforced server-side; clients are untrusted.
- Validate input, sanitize output, apply least privilege, and implement rate limiting where appropriate.
- For high-risk systems (payments, crypto, admin panels), apply extra controls (see Security section).

---

## Quick Reference — Paste at the Top of Every Prompt

**Purpose:** Universal, non-negotiable development rules applicable to ANY software project
**Scope:** General-purpose — not specific to any particular technology, framework, or domain

### 🚫 What NOT to Do
- **Never ship mock data/stubs in production** — Mocks allowed only in tests/dev behind explicit toggles + CI guards
- **Never use `as any`** in TypeScript unless absolutely necessary and documented
- **Never leave temporary code** — No commented-out code, unused imports, or unused variables
- **Never hardcode data** — Use configuration files, environment variables, or database queries
- **Never introduce errors** — Zero ESLint errors, zero TypeScript errors, zero warnings allowed
- **Never skip testing** — Follow repo coverage gates; new/changed meaningful logic must be fully tested
- **Never overwrite files** without explicit permission — Build incrementally in small steps
- **Never duplicate features/files** — search and reuse existing patterns first

### ✅ What TO Do
- **Always build deterministically** — Small, incremental, reversible steps; pure functions must produce identical outputs for identical inputs
- **Always document changes** — Update `README.md` `todo.md` (run/test docs) and `docs/CHANGELOG.md` (what changed + why)
- **Always follow security best practices** — strict typing, lint/format enforcement, no secrets in repo
- **Always be i18n-ready** — Externalize all user-facing strings; default locales can be EN+ES unless the project specifies otherwise
- **Always build translation-ready** — Use locale/message files, parameterized messages, locale-safe formatting, avoid baked-in text in images, consider RTL/layout, and keep locale parity tests where applicable
- **Always clean up unused code** — If an import/variable/function is unused, use it correctly OR remove it and document why in `CHANGELOG.md`

---

# Universal AI Development Guidelines

## ❤️ Introduction and Confirmation Protocol

This document contains **non-negotiable** rules for AI-assisted development. You must read, understand, and apply all rules relevant to the project’s tags.

### ✅ Mandatory First-Response Confirmation
To confirm you processed this file, your **first response** for any new task must include:

1) **All emojis below (exactly once each):**
- **❤️** (Introduction & Confirmation)
- **🎭** (Strategic Role & Research)
- **🧩** (Holistic Development)
- **🛡️** (No Feature Degradation)
- **📋** (Project & Task Management)
- **🌟** (Development Workflow)
- **🧪** (Testing & Reliability)
- **📝** (Code Quality & Style)
- **✔️** (Finalization & Task Completion)
- **✅** (Version Control & CI)
- **🧠** (Global Confirmation of All Rules)

2) **A short “readback” block** (5–10 lines max):
- Detected project type + stack (e.g., Next.js/Node/Expo/Python)
- Applicable tags you’ll enforce (e.g., `[WEB][API][SECURITY][EXISTING-REPO]`)
- Top 5 non-negotiables for this task (in your own words)
- What docs/tracking files you will update (`todo.md`, `FEATURES.md`, `CHANGELOG.md`, etc.)

---

## 🏷️ Tag System (Apply Only What Fits)

Rules include tags. Apply **all** rules that match the project context.

- `[ALL]` always apply
- `[EXISTING-REPO]` when modifying an existing project
- `[GREENFIELD]` when starting a new project
- `[WEB]` web apps (React/Next/Vite, etc.)
- `[MOBILE]` mobile apps (React Native/Expo, etc.)
- `[BACKEND]` backend services (Node/Python/etc.)
- `[API]` any API surface (REST/GraphQL/gRPC/webhooks)
- `[SaaS]` multi-tenant / subscription / enterprise features
- `[CRYPTO]` blockchain/smart contracts/wallet interactions
- `[INFRA]` deployment/CI/IaC/cloud provisioning
- `[HIGH-RISK]` money, auth, admin, crypto, PII, compliance, etc.

---

## 🎭 Strategic Role & Research‑Driven Protocol `[ALL]`

1. **Define Your Role**: Before any action, analyze the prompt and project goals to define your function (e.g., **Code Architect**, **Security Analyst**, **Refactoring Specialist**). Document this role in your planning file.
2. **Research First, Act Second**: Use available tools to confirm best practices for the technologies involved. **Never use trial-and-error** when correctness/safety matters.
3. **Formulate a Strategy**: Create a step-by-step plan in `todo.md`. Explain *why* the plan is optimal.
4. **Implement with Confidence**: Execute systematically, verifying after each step.

**Prohibited:** Coding without a defined role, using outdated assumptions, following patterns without verifying they fit this repo, or guessing APIs/paths.

---

## 🧠 Repo Intelligence & Non‑Duplication Protocol `[ALL][EXISTING-REPO]`

Before writing any code in an existing repo:

1) **Map the repo**
- Identify entrypoints, routing, core modules, shared utilities, and existing patterns.
- Identify testing stack and coverage tooling (Jest/Vitest/Playwright/Cypress/Pytest/etc.).
- Identify CI config and existing quality gates.

2) **Search for existing implementations**
- Search for feature names, routes, components, services, models, API endpoints, and similar utilities.
- If something exists: **extend/refactor** it. Do not rebuild a parallel version.

3) **Create new files only when necessary**
- If new files are needed, place them where the repo already expects them (follow existing conventions).
- Keep changes incremental and reversible.

---

## 🧩 Holistic Development Approach `[ALL]`

Approach every task from three perspectives:
- **Developer**: clean, maintainable, scalable, best-practice code.
- **Owner**: business value, simplicity, low operational burden.
- **User**: usability, performance, clarity, accessibility, localization readiness.

- **Proactive Improvement**: Don’t just follow instructions. Look for quality, performance, and UX wins — but **always confirm it’s not already implemented**.
- **Maintain Quality Interaction**: If a conversation becomes too long or loses focus, suggest starting fresh to preserve clarity.

---

## 🔄 Web/Mobile Feature Parity Rule `[WEB][MOBILE]`

When a project has both web and mobile versions:
- Any feature implemented on one platform must be implemented on the other unless explicitly out of scope.
- Keep shared business logic consistent; avoid divergent rules.
- Document any intentional differences in `FEATURES.md` and `CHANGELOG.md`.

---

## 🛡️ CRITICAL PRINCIPLE: No Feature Degradation `[ALL]`

- **Never remove or disable an existing feature** just to complete a new task faster.
- If something breaks: **fix it**; do not cut it.
- If an old feature is outdated: refactor and preserve behavior unless explicitly approved to change.

---

## 📋 Project & Task Management `[ALL]`

### Project awareness (always)
- **Read `PLANNING.md` first** (if present) to understand architecture, goals, constraints, and conventions.
- Also scan: `README.md`, `FEATURES.md`, existing `todo.md`, and any `/docs` architecture notes.

### Required tracking files (create if missing)
- `todo.md` — task plan + checklist + results
- `SCRATCHPAD.md` — detailed notes, research findings, alternatives considered
- `PROMPT.md` — progress log, decisions, and lessons learned (per-task or per-project; keep short but useful)
- `docs/CHANGELOG.md` — what changed + why
- `README.md` — how to run/test/build/deploy
- `FEATURES.md` — feature registry (required for product apps; optional for tiny scripts)

### Task planning workflow
- For every new assignment, create or update `todo.md`:
  1. **Create a plan**: Write a detailed plan with a checklist of to-do items.
  2. **Verify plan**: Before coding, **present the plan for verification**.
  3. **Track progress**: Mark items as complete (`[x]`) as you work.

### Scratchpad usage
- Use `SCRATCHPAD.md` for:
  - exploring multiple solutions
  - capturing pitfalls/edge cases
  - recording what you searched and what you found
  - noting version constraints and repo-specific conventions

### Checkbox strategy (IMPORTANT)
- **Do not** check boxes inside this global file.
- Copy the **Task Completion Checklist template** (Appendix) into `todo.md` for the current task, then check it there.
- If another agent worked before you, do not trust their checkmarks — verify and check your own items.

---

## 📦 Feature Documentation & Registry `[ALL]`

Purpose: prevent forgotten features and ensure launch/marketing parity.

This file is the source of truth for:
- White papers and documentation
- User manuals and help guides
- Marketing materials and landing pages
- Onboarding new developers

- Include **feature name**, **brief description**, and **last-modified date** (or a link to the PR/commit).

### Categories required (adjust to project)
- User Features
- Admin Features
- Developer/Infrastructure Features
- Backend/API Features

### When to update
- Every time you add, change, or remove a feature (including hidden backend-only features).
- Every time a feature status changes (planned → in progress → done).

### Format example
```md
## 👤 User Features
- [ ] Feature A — short description
- [x] Feature B — short description

## 🛠️ Admin Features
- [ ] Feature C — short description

## 🧰 Developer/Infra Features
- [ ] CI pipeline — lint/typecheck/test/build

## 🔌 Backend/API Features
- [ ] /api/example — request/response contract documented
```

---

## 🌟 The Development Workflow `[ALL]`

### Step 0: Pre‑Flight (Existing Repo Safety) `[EXISTING-REPO]`
- Confirm project type + stack + tooling.
- Confirm whether CI exists and what the gates are.
- Confirm whether mocks are used and how they’re gated.
- Confirm coverage thresholds (where configured).
- Confirm if API contracts exist and how they’re maintained.

### Step 1: Pre‑Implementation
- **Thorough analysis:** Identify the precise root cause of the issue/change. Be **100% certain** before proposing a fix.
- **Simplicity is key:** Design changes to be as simple as possible; impact the minimum code needed.
- Deeply analyze the request and current codebase.
- Identify the simplest, safest change that achieves the goal.
- Update `todo.md` with the plan and verification steps.

### 🧪 Step 2: Test‑Driven Development (TDD)
- **Write tests first:** Before writing implementation code, write the tests that validate the new functionality. These tests should **fail initially**.
- Write tests for the intended behavior before implementation when feasible.
- At minimum, add tests **with** the change (no untested critical logic).
- Include: success case, failure case, edge case, permission/role case (if applicable).
- **Test organization**: Prefer a dedicated `tests/` folder that mirrors the main application structure (follow repo conventions).

### 📝 Step 3: Implementation & Code Quality
- **Focused changes:** Make only the necessary modifications; do not touch unrelated code.
- **Provide high-level explanations:** With each step or meaningful change, provide a concise explanation of what changed and why.
- Implement in small steps; run tests after each meaningful change.
- Keep components/modules focused; refactor if files become overly large.
- **😋 Component size guidelines (React/Web/Mobile where applicable):**
  - Aim for **200–250 lines** per component/file.
  - Files exceeding **500 lines** must be refactored into smaller, single-responsibility modules (extract subcomponents, hooks, utilities).
- Use strict typing; avoid `any` and unsafe casts.
- Use type hints and data validation for clarity and reliability.
- Externalize strings (i18n-ready).
- No dead code, no TODOs, no commented-out blocks.
- **Documentation as you go:**
  - Write clear **docstrings** for every function/module where the repo expects them (e.g., Google style).
  - Add inline comments like `# Reason: ...` only for complex logic.
  - Update `PROMPT.md` with progress, key decisions, and lessons learned.
- Add professional comments only where they explain **why**, not what.

### ✔️ Step 4: Finalization & Task Completion
- Run full verification: lint, typecheck, all tests, coverage, build.
- Update `README.md` if run/test/build instructions changed.
- Ensure any new user-facing text is added to localization/i18n message files.
- Update `docs/CHANGELOG.md` with what changed and why.
- Update `FEATURES.md` if any features changed/added.
- In `todo.md`, add a final **Review** section summarizing work and results.
- Mark the main task complete in `todo.md`.

---

## 🧪 Testing & Reliability Playbook `[ALL]`

### Principles
- Prefer many fast unit tests, some integration tests, and a small number of E2E tests for critical paths.
- Tests must be deterministic (no flaky timers, uncontrolled randomness, or dependence on external systems without isolation).
- Use mocks/stubs **only** to isolate external dependencies (network, payment providers, third-party APIs) — never to “fake” core business logic.

### Minimum test set by project type
- `[WEB]` Unit + Integration + at least 1–3 critical E2E flows (auth, purchase, onboarding, etc.)
- `[MOBILE]` Unit + Integration + at least 1–2 device E2E flows (login, primary flow)
- `[API][BACKEND]` Unit + Integration + contract tests + authz tests
- `[SaaS]` Add multi-tenant isolation tests + billing edge cases + basic load test scenario
- `[CRYPTO]` Unit + integration + fork tests (where relevant) + fuzz/invariant tests for critical contracts

### Recommended tooling (choose what matches the repo)
- Web: Jest/Vitest + Testing Library + Playwright/Cypress + MSW (for dev/test network isolation)
- Mobile: Jest + Maestro/Detox (or repo equivalent)
- Backend: Supertest/HTTP clients + DB test containers (or repo equivalent)
- Crypto: Hardhat/Foundry + mainnet forking + Slither/static analysis + fuzzing tools

### Impersonation / “View As User” testing (when applicable) `[WEB][SaaS]`
- If implementing impersonation to debug user state:
  - Must be restricted to privileged roles only.
  - Must log every action (audit trail).
  - Must visibly indicate impersonation mode.
  - Prefer read-only mode unless explicitly required otherwise.

---

## 🎭 Mock Data Policy

**Real API/Backend calls are ALWAYS the default. Mock data should only exist behind an explicit feature toggle.**

### Rules:
1. **Default to real** - All screens and features should use real API/backend calls by default
2. **Mock ONLY with toggle** - Mock data is ONLY acceptable when behind a dev mode feature flag
3. **Toggle location** - Create a central config file with a single boolean to control mock vs real
4. **Purpose of mock** - Mock data is for demos and UI design only, never for actual development
5. **No hardcoded mock** - Never leave mock data inline without the toggle mechanism
6. **No prod leak** - Mocks must be impossible to enable in production (see Critical Gates)

### Implementation Pattern:
```js
// Central config file
DEV_CONFIG = {
  USE_MOCK_DATA: false, // Default OFF = real API
}

// In screens/components:
if (DEV_CONFIG.USE_MOCK_DATA) {
  // Use mock data for demo
} else {
  // Use real API/backend
}
```

### Hard guards (required):
- Env gating: `NODE_ENV !== 'production'` AND `ENABLE_MOCKS === 'true'`
- CI guard: production build must fail if mocks are enabled or imported outside allowed locations
- Lint guard: forbid `/mocks/` imports in production paths
- Runtime guard: crash loudly if production env attempts to enable mocks

---

## ✅ Version Control, CI/CD & DevOps `[ALL][INFRA]`

### Pre‑commit / pre‑merge verification
- Before suggesting a commit, you must confirm:
  - All tests pass (unit/integration/E2E as applicable).
  - Lint + typecheck pass with zero errors/warnings.
  - Coverage meets configured thresholds.
  - Production build succeeds (where applicable).



**Strict pass criteria:** You may only suggest a commit if all of the following are true:
- **Zero** failing tests
- **Zero** linter/typechecker errors
- **Zero** warnings
- Coverage meets or exceeds configured thresholds

- **Pushing to GitHub:** A `git push` may only be suggested after a successful commit under the criteria above.
### Coverage policy (how to decide thresholds)
- **If thresholds exist:** follow them and do not lower them without explicit approval.
- **If thresholds do not exist:** create them and document the rationale. Default guidance:
  - New/changed meaningful code: target 100%
  - Repo gate: high baseline (≈90%+ overall) with explicit allowlisted exclusions

### CI pipeline (minimum)
- `lint → typecheck → test → coverage → build` on every PR/push.
- Include **mock-leak guard** and **secret scanning** where possible.

### Deployments & environments (12-factor mindset)
- Configuration belongs in environment variables / secret managers, not source.
- Keep dev/staging/prod behavior consistent where possible.
- If infra exists: prefer Infrastructure-as-Code (Terraform/Pulumi/CDK/etc.) and document how to provision it.

### Commit after 10+ changes protocol (keep)
- After resolving **10+ issues/changes** AND passing full verification, include:
  - **"✅ 10+ issues/changes fixed successfully after passing all verification checks."**

---

## 📜 API Contracts & Schema Discipline `[API][BACKEND][WEB]`

- Every API surface should have a clear contract (OpenAPI / GraphQL schema / Protobuf / JSON Schema).
- If the project already uses a contract format, follow it.
- If none exists and you are creating an API, add a contract and basic contract tests.
- Changes must be backwards compatible unless explicitly approved to be breaking.

---

## 🛡️ Comprehensive Security Audit & Code Review Requirements `[ALL][HIGH-RISK]`

### Phase 1: Security Audit
1) **Frontend Security Review**
- Scan frontend files for hardcoded API keys, passwords, tokens, or sensitive config
- Verify no DB connection strings, internal URLs, or admin creds are exposed
- Check for XSS in user input handling/rendering
- Validate secure auth token storage (avoid localStorage for sensitive tokens)
- Ensure HTTPS-only cookies / secure headers as applicable
- Review CORS for appropriate origin restrictions

2) **Backend Security Review**
- Audit endpoints for auth + authz checks
- Validate input validation and sanitization
- Check for injection risks in queries
- Ensure sensitive data is hashed/encrypted correctly
- Validate rate limiting/throttling where needed
- Review error handling for info disclosure
- Ensure sensitive config uses environment variables

3) **Authentication & Authorization**
- JWT/session follows best practices (expiry, rotation, revocation strategy if needed)
- RBAC enforced consistently
- Token/session expiration handled correctly
- Password policy + secure storage mechanisms (if passwords exist)

### Phase 2: Detailed Code Walkthrough (when delivering a full system)
- Architecture overview + data flows + auth flow
- Security implementations (before/after where relevant)
- Feature breakdown (major features, DB schema, API docs)
- Code quality patterns + error handling + performance + testing approach

### Domain-specific add-ons (apply as relevant)
- `[WEB]` Secure headers, CSRF strategy where needed, XSS sanitization, strict CORS
- `[MOBILE]` Treat client as untrusted; use OS secure storage for tokens; never embed secrets in the app
- `[SaaS]` Multi-tenant isolation, audit logs, MFA/SSO where applicable, encryption at rest/in transit for sensitive data
- `[CRYPTO]` Never store PII on-chain; use fork tests + fuzz tests; enforce admin actions via multisig/timelock patterns where relevant

---

## 🎓 Student‑Friendly Communication Rule `[ALL]`

- Explain things clearly and step-by-step.
- Use **What / Why / How** structure when teaching.
- Define jargon briefly before using it.
- **Important:** Keep *code comments* professional/minimal; do the teaching in the chat and docs, not as “tutorial comments” in code.

---

## 🚫 Never Assume, Never Guess Rule `[ALL]`

- If you aren’t sure, research the repo and/or official docs.
- Do not invent file paths, APIs, env vars, or libraries.
- If the requirement is unclear, ask — do not guess.

---

## 💬 Professional Code Comments Rule `[ALL]`

### AI Code Artifacts to AVOID ❌
- Comments that narrate obvious code (`// set x to 5`)
- “As an AI…” references or meta commentary
- Overly verbose tutorial-style comments inside production code

### Professional Commenting Style ✅
```javascript
// Only comment non-obvious business logic
const fee = amount * 0.19; // 19% platform fee (configurable)

// Comment complex algorithms or domain-specific rules
function calculatePrizeDistribution(winners, totalPool) {
  // Distribution: configurable; default example 50/25/10 + remainder for 4th-10th
}
```

### The Professional Standard
- Comment **why** a decision exists, especially for business rules, edge cases, and constraints.
- Avoid comments that become stale; prefer self-explanatory code + tests.
- **DO**: Explain what the code does and why (`// Validate user session before API call`)
- **DON'T**: Reference fixes or AI actions (`// Fixed bug where X was broken`, `// Removed Y because it caused Z`)
- Comments should read naturally for onboarding developers, not as a changelog of fixes.


---

## 🎛️ Admin Dashboard Configurability Principle

**If the project has an admin dashboard: Everything that might need to change should be editable via the dashboard, not in code.**

### First: Analyze the Project
Before implementing admin features, analyze what the project needs:
- Does it have an admin dashboard? → If yes, apply these rules
- What authentication does it use? → Google, email, wallet, phone, etc.
- Who are the admin users? → CEO, CTO, developers, moderators

### Must Be Dashboard-Configurable (when applicable):
1. **Fees & Pricing** - Any percentages, prices, or costs
2. **API Keys** - Third-party service credentials (stored securely)
3. **Business Rules** - Limits, thresholds, durations
4. **Feature Toggles** - Enable/disable features without deploying
5. **App Content** - Announcements, FAQ, legal text
6. **Rate Limits** - Request limits, cooldowns

### Why This Matters:
- Non-developers can adjust settings without code changes
- No deployment needed for configuration updates
- Safer than hardcoding values that may change
- Enables A/B testing and gradual rollouts

---

## 🔐 Role Hierarchy & Access Control (For Projects with Admin Systems)

**When building admin functionality, implement a clear role hierarchy.**

### Role Structure Template:
```
Owner/CTO
  ├── Can add/remove all other roles
  ├── Can edit all settings
  ├── Can view all data
  └── Can grant/revoke specific permissions
       │
       ├── CEO/Business Owner
       │   ├── Business settings
       │   ├── Fee/pricing configuration
       │   └── User management
       │
       ├── Developer
       │   ├── API configuration
       │   ├── Feature toggles
       │   └── Technical settings
       │
       └── Admin/Moderator
           ├── User support
           └── Content moderation
```

### Admin Authentication (Analyze Per Project):
Before implementing, determine what auth methods the project uses:
- **Wallet-based projects** → Admins sign in by connecting wallet, permissions matched by wallet address
- **Google/Social auth projects** → Admins sign in with Google/email, permissions matched by email
- **Email/password projects** → Standard admin login with role-based permissions
- **Hybrid projects** → Support multiple auth methods, identify user by whichever method they use

**Key Rule:** Only the top-level role (Owner/CTO) can add new team members and adjust their permission levels. The dashboard should automatically identify roles and grant appropriate access based on the configured authentication method.

---

## ⛓️ Blockchain & Cross-Chain Readiness (For Web3 Projects)

**When building blockchain-integrated applications, design for flexibility and cross-chain compatibility.**

### Design Principles:
1. **Abstract the chain layer** - Don't hardcode chain IDs, RPC URLs, or contract addresses
2. **EVM-first, but flexible** - Build for EVM compatibility (Ethereum, BSC, Polygon, etc.) but structure code to swap chains easily
3. **Multi-chain ready** - Design so the same app can support multiple blockchains simultaneously
4. **Bridge-aware** - Consider how assets might move between chains in the future

### Configuration Should Support:
```
Chain Configuration (per environment):
- Chain ID
- RPC URL
- Contract addresses
- Native currency symbol
- Block explorer URL
```

### Why This Matters:
- New blockchains launch frequently
- Gas fees vary dramatically between chains
- Users may prefer different chains
- Bridging assets is common

---

## 📜 Technology‑Specific Development Rules `[ALL]`

### Research First
- Identify the exact stack and versions used.
- Verify best practices in official docs for those versions.

### Apply Context
- Follow repo conventions and patterns (routing, data layer, state, error handling).

### Never Assume
- If you don’t see it in repo or docs, do not claim it exists.

---

## 🔬 Research‑Driven Implementation `[ALL]`

- Research before implementing anything non-trivial (auth, DB, caching, cloud, payments, crypto).
- Prefer proven patterns and official docs over guesswork.

---

## 🔐 Smart Contract & Blockchain Engineering Standards `[CRYPTO][HIGH-RISK]`

### 1) Security‑First Architecture (No “God Mode”)
- No universal withdraw or admin-drain functions without multisig/timelock governance and explicit justification.
- Prefer pull payments, checks-effects-interactions, and reentrancy guards where needed.

### 2) Gas Optimization & Efficiency
- Use appropriate packing and types (e.g., smaller ints where safe).
- Avoid unnecessary storage writes.

### 3) Senior‑Level Solidity Style
- Explicit visibility on vars/functions.
- Use `immutable` for constructor-set values; `constant` for true constants.
- Use NatSpec for public/external functions.

---

## ☑️ Appendix A — Task Completion Checklist Template (Copy into `todo.md`)

```md
### ✅ Task Completion Checklist
- [ ] Read repo docs (README/PLANNING/FEATURES/todo) and confirmed existing patterns
- [ ] Verified feature/file does not already exist (or reused/refactored existing)
- [ ] Implemented change in small steps (no file truncation/overwrite)
- [ ] Added/updated tests (unit/integration/E2E as relevant)
- [ ] Confirmed coverage meets repo thresholds (and touched meaningful code is fully covered)
- [ ] Lint passes (0 errors/warnings)
- [ ] Typecheck passes (0 errors/warnings)
- [ ] Full test suite passes (incl. E2E where relevant)
- [ ] Production build passes (where relevant)
- [ ] Mock-leak guard satisfied (no mock imports in prod paths; ENABLE_MOCKS off in prod)
- [ ] Security review completed for relevant surfaces (auth, input validation, secrets, RBAC)
- [ ] Updated docs/CHANGELOG.md (what changed + why)
- [ ] Updated README.md if run/test/build changed
- [ ] Updated FEATURES.md if features changed/added
- [ ] Added final Review section in todo.md summarizing results
```

---

## 📚 Appendix B — Full Testing Strategies Guide (Embedded)


## Complete Testing Guide for Beginners

> **Welcome!** This guide is written for developers who are learning testing. Everything is explained from scratch - no prior testing knowledge needed.
> 
> **Last Updated**: January 2026
> **Purpose**: Comprehensive testing documentation for Web, Mobile, Crypto, and SaaS applications

---

### Table of Contents

1. [What is Testing and Why Do We Need It?](#1-what-is-testing-and-why-do-we-need-it)
2. [Understanding Your Project Type](#2-understanding-your-project-type)
3. [Web Application Testing](#3-web-application-testing)
4. [Mobile Application Testing](#4-mobile-application-testing)
5. [Crypto & Smart Contract Testing](#5-crypto--smart-contract-testing)
6. [SaaS & API Testing](#6-saas--api-testing)
7. [Implementation Guides](#7-implementation-guides)
8. [Quick Reference: Testing Tools](#8-quick-reference-testing-tools)

---

### 1. What is Testing and Why Do We Need It?

#### What is Testing?

Testing is the process of checking that your application works correctly. Think of it like a quality control check at a factory - before shipping a product, you make sure it works as expected.

**Example**: You built a login button. Testing verifies:
- Does the button appear on the page?
- Does it open the login form when clicked?
- Does it show an error if the password is wrong?
- Does it let the user in with correct credentials?

#### Why Testing is Important (Especially for Beginners)

| Problem | How Testing Helps |
|---------|-------------------|
| You fix one bug and create two new ones | Tests catch regressions immediately |
| You're afraid to change code because it might break | Tests give you confidence to refactor |
| Users report bugs in production | Tests catch bugs before users see them |
| You manually test the same things over and over | Tests automate repetitive checking |
| Your code works on your machine but not on the server | Tests run in consistent environments |

#### The Testing Pyramid (Simple Explanation)

Imagine a pyramid with three layers:

```
         /\
        /  \
       /E2E \\\          ← Few tests (expensive, slow)
      /--------\\
     /Integration\\\       ← Medium tests
    /--------------\\\ 
   /    Unit Tests   \\\   ← Many tests (fast, cheap)
  /--------------------\\\
```

**Unit Tests** (Bottom layer):
- Test individual functions or components
- Very fast (milliseconds)
- You write many of these (70% of your tests)
- Example: Test that a "calculateInterest" function returns correct values

**Integration Tests** (Middle layer):
- Test how parts work together
- Medium speed (seconds)
- Example: Test that clicking "Deposit" calls the API and updates the balance

**E2E Tests** (Top layer):
- Test the entire application like a real user
- Slow (seconds to minutes)
- You write few of these (10% of your tests)
- Example: Test that a user can sign up, deposit money, and see their balance

---

### 2. Understanding Your Project Type

Different projects need different types of testing. Here's how to identify yours:

#### Type A: Web Application (What You Have)
**Characteristics**:
- Runs in a web browser
- Built with React, Next.js, Vue, Angular, etc.
- Users visit a URL to use it
- Examples: Dashboards, websites, web apps

**Your Testing Focus**:
- ✅ Unit tests for components and functions
- ✅ API mocking for offline development
- ✅ E2E tests for critical user flows
- ✅ Visual regression testing

#### Type B: Mobile Application
**Characteristics**:
- Runs on phones (iOS/Android)
- Built with React Native, Flutter, Swift, Kotlin
- Users download from App Store/Play Store
- Examples: Mobile banking apps, social media apps

**Your Testing Focus**:
- ✅ Unit tests for logic
- ✅ Device testing (different phone sizes)
- ✅ E2E tests with real device automation
- ✅ Performance testing (battery, memory)

#### Type C: Crypto/DeFi Application
**Characteristics**:
- Interacts with blockchain
- Has smart contracts
- Handles real money/tokens
- Examples: Yield platforms, DEXs, NFT marketplaces

**Your Testing Focus**:
- ✅ Smart contract unit tests
- ✅ Mainnet forking (test with real data)
- ✅ Fuzz testing (find edge cases)
- ✅ Security analysis

#### Type D: SaaS Platform
**Characteristics**:
- Software as a Service
- Has backend APIs
- Multiple users/tenants
- Examples: Email services, project management tools

**Your Testing Focus**:
- ✅ API contract testing
- ✅ Load testing (many users)
- ✅ Integration tests
- ✅ Feature flags for safe deployment

---

### 3. Web Application Testing

#### Test 1: User Impersonation (Already Implemented!)

**What is it?**
User Impersonation allows you to view any user's account without their password or private keys. You enter their wallet address, and you see exactly what they see.

**Why is it useful?**
- **Debug user issues**: A user says "my balance is wrong" - you can impersonate them and see exactly what they see
- **Test with real data**: Instead of creating fake test data, you can use real user accounts
- **Demo to stakeholders**: Show realistic data without using your own account
- **Support investigations**: See what a user sees when they report problems

**How it works:**
1. You enter a wallet address (e.g., `0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6`)
2. The app fetches that user's data from the blockchain
3. You see their dashboard, balance, transactions - everything they see
4. **Important**: You cannot make transactions (spend their money) - it's read-only

**Security (How We Protect It):**
```typescript
// This is the logic we use in your app:

// 1. Check if impersonation is enabled globally
if (!IMPERSONATION_ENABLED) return null;

// 2. In development: show to everyone
if (process.env.NODE_ENV === 'development') return true;

// 3. In production: ONLY show if connected wallet is CTO
if (process.env.NODE_ENV === 'production') {
  return connectedWallet === CTO_WALLET;
}
```

**How to use it in your app:**
1. Look for the purple eye icon (bottom-right corner in development)
2. In production, only you (CTO) will see a red lock icon
3. Click it, enter any wallet address
4. The app will show that user's data
5. Click "Clear" to go back to your own account

**When to use:**
- ✅ Debugging a specific user's issue
- ✅ Testing how the UI looks with different data
- ✅ Demonstrating the app with realistic data
- ❌ Never for unauthorized access to user data (always have permission)

**🛡️ Security Best Practices (Crucial):**
While powerful, "God Mode" is risky. Professional implementations require:
1.  **Audit Logs:** Always log the `impersonator_id`, `target_user_id`, and `timestamp` for every action taken.
2.  **Visual Indicators:** Display a persistent, bright banner (e.g., "IMPERSONATING USER X") to prevent accidental data modification.
3.  **Read-Only Mode:** If possible, disable "write" operations (POST/PUT/DELETE) during impersonation sessions to prevent data corruption.
4.  **JWT Claims:** If using tokens, add a claim like `act_as: target_user_id` to the token rather than swapping the `user_id`. This preserves the audit trail in the backend.

---

#### Test 2: API Mocking with MSW (Mock Service Worker)

**Status**: Ready to implement  
**Estimated Setup Time**: 10 minutes  
**Cost**: Free (Open Source)

**What is it?**
MSW intercepts your app's API calls and returns fake responses. It's like having a fake server that responds instantly.

**Why is it useful?**
- **Work without backend**: Build the frontend before the API is ready
- **Test error states**: Easily simulate "server down" or "rate limit" scenarios
- **Consistent data**: Tests always get the same responses
- **Offline development**: Work on planes or with bad internet
- **Fast tests**: No waiting for real API responses

**Real-world analogy:**
Imagine you're training to be a pilot. Instead of using a real plane (which is expensive and dangerous), you use a flight simulator. MSW is like a flight simulator for your APIs.

**How it works:**
```
Your App → MSW intercepts → Returns mock data
                ↓
          (No real API call made)
```

**Step-by-Step Implementation:**

**Step 1: Install MSW**
```bash
cd apps/web
npm install msw --save-dev
```

**Step 2: Create the mock service worker file**
Create `apps/web/mocks/browser.ts`:
```typescript
// mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
```

**Step 3: Create mock handlers**
Create `apps/web/mocks/handlers.ts`:
```typescript
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  // Mock user balance API
  http.get('/api/user/balance/:address', ({ params }) => {
    return HttpResponse.json({
      address: params.address,
      balance: '1500.50',
      currency: 'USDT',
      lastUpdated: new Date().toISOString()
    });
  }),
  
  // Mock transaction history
  http.get('/api/user/transactions/:address', () => {
    return HttpResponse.json({
      transactions: [
        { id: 1, type: 'deposit', amount: '1000', date: '2026-01-20' },
        { id: 2, type: 'withdrawal', amount: '500', date: '2026-01-22' },
      ]
    });
  }),
  
  // Mock error response
  http.get('/api/error-example', () => {
    return new HttpResponse(
      JSON.stringify({ error: 'Server overloaded' }), 
      { status: 503 }
    );
  }),
  
  // Mock referral data
  http.get('/api/user/referrals/:address', () => {
    return HttpResponse.json({
      totalReferrals: 5,
      totalEarnings: '250.00',
      referrals: [
        { address: '0x123...', joined: '2026-01-15', earnings: '50' },
        { address: '0x456...', joined: '2026-01-18', earnings: '200' },
      ]
    });
  })
];
```

**Step 4: Initialize MSW in your app**
Modify `apps/web/app/layout.jsx`:
```typescript
// Add at the top of the file
async function enableMocking() {
  if (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_ENABLE_MSW === 'true') {
    const { worker } = await import('../mocks/browser');
    return worker.start();
  }
  return Promise.resolve();
}

// In your RootLayout component
export default function RootLayout({ children }) {
  // Enable mocking before rendering
  useEffect(() => {
    enableMocking().then(() => {
      console.log('🔶 MSW enabled - API calls are mocked');
    });
  }, []);
  
  // ... rest of your layout
}
```

**Step 5: Add environment variable**
Add to `.env.local`:
```
NEXT_PUBLIC_ENABLE_MSW=true
```

**Step 6: Run your app**
```bash
pnpm dev
```

You should see in console: `🔶 MSW enabled - API calls are mocked`

**When to use:**
| Situation | Use MSW? |
|-----------|----------|
| Backend API not ready yet | ✅ Yes |
| Testing error scenarios | ✅ Yes |
| Working offline | ✅ Yes |
| Writing automated tests | ✅ Yes |
| Testing real API performance | ❌ No |
| Testing API authentication | ❌ No |

---

#### Test 3: End-to-End (E2E) Testing with Playwright

**Status**: Ready to implement  
**Estimated Setup Time**: 15 minutes  
**Cost**: Free (Open Source)  
**Website**: https://playwright.dev

**What is it?**
E2E tests automate a real browser. The computer clicks buttons, fills forms, and navigates pages just like a human would.

**Why is it useful?**
- **Tests real user flows**: "Can a user sign up, deposit, and withdraw?"
- **Catches integration bugs**: Problems that only appear when everything works together
- **Cross-browser testing**: Test Chrome, Firefox, Safari automatically
- **Confidence**: Know your critical flows work before deploying

**Real-world analogy:**
It's like having a robot user who tests your app 24/7. The robot follows a script: "Click here, type this, expect to see that."

**Step-by-Step Implementation:**

**Step 1: Install Playwright**
```bash
cd apps/web
npm init playwright@latest
```

This will:
- Install Playwright package
- Create `playwright.config.ts`
- Create example tests in `tests/` folder
- Install browser binaries

**Step 2: Configure Playwright**
Modify `apps/web/playwright.config.ts`:
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile viewport
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

**Step 3: Create your first test**
Create `apps/web/e2e/dashboard.spec.ts`:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('should display user balance', async ({ page }) => {
    // Go to dashboard with impersonation
    await page.goto('/admin/impersonate?address=0x7953A2BE711dE0dd5d9f6797526c16e1e4a4e656');
    await page.goto('/dashboard');
    
    // Check balance is visible
    await expect(page.locator('[data-testid="balance-card"]')).toBeVisible();
    
    // Check it contains a number
    const balanceText = await page.textContent('[data-testid="balance-amount"]');
    expect(balanceText).toMatch(/\d+/);
  });

  test('should navigate to deposit page', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click deposit button
    await page.click('[data-testid="deposit-button"]');
    
    // Should be on deposit page
    await expect(page).toHaveURL(/.*deposit/);
    
    // Deposit form should be visible
    await expect(page.locator('[data-testid="deposit-form"]')).toBeVisible();
  });

  test('should show transaction history', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Scroll to transactions
    await page.click('text=Transactions');
    
    // Transaction list should be visible
    await expect(page.locator('[data-testid="transaction-list"]')).toBeVisible();
  });
});
```

**Step 4: Add data-testid to your components**
In your React components, add test IDs:
```tsx
// Before
<button className="btn-primary">Deposit</button>

// After (for testing)
<button 
  className="btn-primary" 
  data-testid="deposit-button"
>
  Deposit
</button>
```

**Step 5: Run tests**
```bash
## Run all tests
npx playwright test

## Run with UI mode (see tests running)
npx playwright test --ui

## Run specific test file
npx playwright test dashboard.spec.ts

## Run in headed mode (see browser)
npx playwright test --headed
```

**Step 6: View test results**
```bash
## Open HTML report
npx playwright show-report
```

**Best Practices:**
```typescript
// ✅ DO: Use data-testid for stable selectors
await page.click('[data-testid="deposit-button"]');

// ❌ DON'T: Use CSS classes (they change often)
await page.click('.btn-primary'); // Fragile!

// ❌ DON'T: Use text content (it changes with translation)
await page.click('text=Submit'); // Breaks with i18n!
```

**When to use:**
- ✅ Critical user flows (signup → deposit → withdraw)
- ✅ Before each deployment (CI/CD)
- ✅ Regression testing (make sure old features still work)
- ❌ Testing every single edge case (use unit tests instead)

---

#### Test 4: Error Monitoring with Sentry

**Status**: Ready to implement  
**Estimated Setup Time**: 10 minutes  
**Cost**: Free tier (5,000 errors/month)  
**Website**: https://sentry.io

**What is it?**
Sentry tracks errors that happen in your production app, so you know when users encounter bugs.

**Why is it useful?**
- **Know about bugs**: Users don't report bugs, they leave
- **Context**: See what user was doing when error occurred
- **Prioritization**: Know which errors affect most users
- **Free tier**: 5,000 errors/month for free (perfect for small apps)

**Is it free?**
**YES!** Sentry has a generous free tier:
- 5,000 errors per month
- 1 user (you)
- 30-day data retention
- All features included

**Step-by-Step Implementation:**

**Step 1: Create a Sentry account**
1. Go to https://sentry.io/signup/
2. Sign up with your email or GitHub
3. Create a new project:
   - Platform: React
   - Project name: yieldable-web
4. Copy your DSN (looks like: `https://xxx@yyy.ingest.sentry.io/zzz`)

**Step 2: Install Sentry SDK**
```bash
cd apps/web
npm install @sentry/nextjs
```

**Step 3: Configure Sentry**
Create `apps/web/sentry.client.config.ts`:
```typescript
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Set environment
  environment: process.env.NODE_ENV,
  
  // Adjust this value in production
  tracesSampleRate: 1.0,
  
  // Replay settings (see user actions leading to error)
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  
  integrations: [
    Sentry.replayIntegration({
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],
  
  // Don't send errors in development
  beforeSend(event) {
    if (process.env.NODE_ENV === 'development') {
      return null;
    }
    return event;
  },
});
```

Create `apps/web/sentry.server.config.ts`:
```typescript
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
```

Create `apps/web/sentry.edge.config.ts`:
```typescript
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
```

**Step 4: Create error boundary component**
Create `apps/web/components/ErrorBoundary.tsx`:
```typescript
'use client';

import * as Sentry from '@sentry/nextjs';
import Error from 'next/error';
import { useEffect } from 'react';

export default function GlobalError({ error }: { error: Error }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body>
        <Error statusCode={500} title="Something went wrong!" />
      </body>
    </html>
  );
}
```

**Step 5: Add environment variable**
Add to `.env.local`:
```
NEXT_PUBLIC_SENTRY_DSN=https://your-dsn-here@sentry.io/project-id
```

**Step 6: Update next.config.js**
Modify `apps/web/next.config.mjs`:
```javascript
const { withSentryConfig } = require('@sentry/nextjs');

const nextConfig = {
  // your existing config
};

module.exports = withSentryConfig(nextConfig, {
  org: 'your-org-name',
  project: 'yieldable-web',
  silent: !process.env.CI,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
});
```

**Step 7: Test Sentry**
Add a test error button somewhere:
```tsx
<button onClick={() => {
  throw new Error('Test Sentry Error');
}}>
  Test Error
</button>
```

Click it in production (or remove the development check temporarily).

**What you get:**
- ✅ Email alerts when errors occur
- ✅ Stack traces showing where error happened
- ✅ User actions leading to the error (replay)
- ✅ How many users affected
- ✅ Browser and device information

**When to use:**
- ✅ All production apps
- ✅ From day one
- ✅ Even solo projects
- ✅ It's free!

---

#### Test 5: Visual Regression Testing with Chromatic + Storybook

**Status**: Optional (can implement later)  
**Estimated Setup Time**: 30 minutes  
**Cost**: Free for open source, paid for private repos  
**Website**: https://www.chromatic.com

**What is it?**
Visual regression testing automatically detects when your UI changes. It takes screenshots and compares them to detect unexpected changes.

**Why is it useful?**
- **Catches UI bugs**: "The button moved 2 pixels left" or "The color changed"
- **No test code needed**: Just write Storybook stories
- **Review UI changes**: See visual diffs in pull requests
- **Cross-browser**: Test Chrome, Firefox, Safari simultaneously

**Is it free?**
- ✅ **Free** for open source projects (unlimited)
- 💰 **Paid** for private projects (starts at $149/month)
- ✅ **Free tier**: 5,000 snapshots/month for small teams

**Professional Alternatives (Free & Open Source):**
If you need a free option for private repositories, consider:
*   **Lost Pixel:** Runs on GitHub Actions, stores images on your own S3 bucket. Very affordable.
*   **BackstopJS:** Runs locally or in CI. Highly configurable but requires more setup.
*   **Reg-suit:** Compares screenshots in S3 buckets.

**When to use:**
- ✅ Component libraries
- ✅ UI-heavy applications
- ✅ Design system maintenance
- ✅ Before releasing UI changes

**Note**: For a private DeFi project, consider using Chromatic's free tier or the open-source alternative **Loki** (https://loki.js.org/)

---

### 4. Mobile Application Testing

#### Test 1: E2E Testing with Maestro (React Native)

**Status**: For mobile apps  
**Estimated Setup Time**: 20 minutes  
**Cost**: Free (Open Source)  
**Website**: https://maestro.mobile.dev

**What is it?**
Maestro is a tool that automates testing on real mobile devices. You write simple YAML files describing what to tap and what to check.

**Installation:**
```bash
## macOS
curl -Ls "https://get.maestro.dev" | bash

## Windows (via Chocolatey)
choco install maestro

## Or download from: https://github.com/mobile-dev-inc/maestro/releases
```

**Step-by-Step Implementation:**

**Step 1: Create test file**
Create `apps/mobile/maestro/deposit-flow.yaml`:
```yaml
appId: com.yieldable.app
---
## Launch the app
- launchApp

## Tap Connect Wallet button
- tapOn: "Connect Wallet"

## Select MetaMask
- tapOn: "MetaMask"

## Wait for and verify Dashboard appears
- assertVisible: "Dashboard"

## Tap Deposit
- tapOn: "Deposit"

## Enter amount
- inputText: 
    selector: "Amount"
    text: "100"

## Tap Confirm
- tapOn: "Confirm"

## Verify success
- assertVisible: "Transaction Submitted"
```

**Step 2: Run the test**
```bash
cd apps/mobile
maestro test maestro/deposit-flow.yaml
```

**When to use:**
- ✅ Critical user flows
- ✅ Testing on real devices
- ✅ Quick mobile automation
- ❌ Complex logic testing (use unit tests)

#### Comparison: Choosing the Right Mobile Tool

| Feature | **Maestro** (Recommended Start) | **Detox** (Advanced) | **Appium** (Legacy/Enterprise) |
|---------|---------------------------------|----------------------|--------------------------------|
| **Type** | **Black Box** (Simulates User) | **Gray Box** (Syncs with App) | **Black Box** (WebDriver) |
| **Speed** | 🚀 Fast | ⚡ Fastest | 🐢 Slow |
| **Flakiness** | Low (Built-in waiting) | Very Low (Syncs with JS thread) | High (Needs manual waits) |
| **Language** | YAML (No coding skills needed) | JavaScript/TypeScript | Java/Python/JS |
| **Best For** | **Solo Devs, Quick Prototypes** | **Complex React Native Animations** | **QA Teams, Native Apps** |

---

#### Test 2: Device Testing on Real Devices

**What is it?**
Testing your app on real physical devices (not just simulators) using cloud services.

**Device Lab Strategy (The Tiered Approach):**
1.  **Tier 1 (Local):** Simulators (iOS Simulator/Android Emulator). Fast, free. Use **Expo Orbit** to instantly launch builds on simulators.
2.  **Tier 2 (Real Device Wrapper):** Connect your *own* phone via USB.
3.  **Tier 3 (Cloud Farm):** Use **BrowserStack** or **AWS Device Farm** only for final compatibility checks on obscure devices (e.g., older Samsungs) before a major release.

**Services:**

| Service | Free Tier | Sign Up Link | Best For |
|---------|-----------|--------------|----------|
| **BrowserStack** | 100 min/month | https://www.browserstack.com/users/sign_up | Cross-platform |
| **AWS Device Farm** | 1000 device min | https://aws.amazon.com/device-farm/ | Enterprise |
| **Firebase Test Lab** | 100 device min/day | https://firebase.google.com/docs/test-lab | Android focus |
| **Expo Orbit** | Unlimited | https://github.com/expo/orbit | iOS simulator |

**When to use:**
- ✅ Before App Store submission
- ✅ Testing on specific devices
- ✅ Reproducing device-specific bugs
- ❌ Everyday development (use simulators)

---

### 5. Crypto & Smart Contract Testing

#### Test 1: Mainnet Forking (ESSENTIAL for Your Trading Bot!)

**Status**: Highly Recommended for Trading Bot  
**Estimated Setup Time**: 20 minutes  
**Cost**: Free (needs RPC endpoint like Alchemy/Infura free tier)

**What is it?**
Mainnet forking creates a local copy of the real blockchain. You can test against real contract states and real token balances.

**Why is it ESSENTIAL for your Trading Bot:**
- **Test with real liquidity pools**: See how your bot behaves with real Uniswap/PancakeSwap data
- **Real token balances**: Test with actual USDT, USDC, WETH amounts
- **No testnet deployment**: Test strategies without spending gas on testnet
- **Accurate price data**: Real market conditions, not fake testnet prices
- **Safe experimentation**: Make trades locally without real money

**Real-world analogy:**
Imagine being able to clone the entire stock exchange to your computer, trade with it, and nothing affects the real market. That's mainnet forking.

**Step-by-Step Implementation:**

**Step 1: Install Hardhat**
```bash
npm install --save-dev hardhat
npx hardhat init
## Choose: Create an empty hardhat.config.js
```

**Step 2: Configure Hardhat for forking**
Create `hardhat.config.js`:
```javascript
require('@nomicfoundation/hardhat-toolbox');

module.exports = {
  solidity: '0.8.19',
  networks: {
    hardhat: {
      forking: {
        url: process.env.ALCHEMY_MAINNET_URL || process.env.QUICKNODE_URL,
        blockNumber: 18000000, // Optional: pin to specific block
        enabled: true
      },
      chainId: 1
    }
  }
};
```

**Step 3: Get an RPC endpoint**
Sign up for a free account:
- **Alchemy**: https://www.alchemy.com/ (Free tier: 300M compute units/month)
- **QuickNode**: https://www.quicknode.com/ (Free tier: 50M credits/month)
- **Infura**: https://www.infura.io/ (Free tier: 100k requests/day)

Get your Mainnet HTTPS URL and add to `.env`:
```
ALCHEMY_MAINNET_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

**Step 4: Impersonate any account (the magic!)**
Create `scripts/test-trading.js`:
```javascript
const { ethers } = require('hardhat');

async function main() {
  // Impersonate a whale (someone with lots of USDT)
  const whaleAddress = '0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6';
  
  await hre.network.provider.request({
    method: "hardhat_impersonateAccount",
    params: [whaleAddress]
  });

  const whale = await ethers.getSigner(whaleAddress);
  
  // USDT contract address on Ethereum
  const USDT_ADDRESS = '0xdAC17F958D2ee523a2206206994597C13D831ec7';
  
  // Get USDT contract
  const usdt = await ethers.getContractAt('IERC20', USDT_ADDRESS, whale);
  
  // Get whale's balance
  const balance = await usdt.balanceOf(whaleAddress);
  console.log(`Whale USDT balance: ${ethers.formatUnits(balance, 6)}`);
  
  // Now you can send yourself USDT!
  const yourAddress = '0xYourAddressHere';
  await usdt.transfer(yourAddress, ethers.parseUnits('10000', 6));
  
  console.log('Transferred 10,000 USDT to your address!');
  
  // Test your trading bot here
  // ...
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

**Step 5: Run the forked network**
```bash
## Terminal 1: Start the forked network
npx hardhat node

## Terminal 2: Run your script
npx hardhat run scripts/test-trading.js --network localhost
```

**For Your Trading Bot Specifically:**
```javascript
// Test your trading strategy with real data
async function testTradingStrategy() {
  // 1. Fork mainnet
  // 2. Impersonate whale with lots of tokens
  // 3. Fund your bot with real tokens
  // 4. Execute trades against real DEXs
  // 5. Measure profit/loss
  // 6. Adjust strategy
  // 7. Repeat without spending real gas!
}
```

**When to use:**
- ✅ Testing DeFi protocols
- ✅ Testing trading bots (ESSENTIAL!)
- ✅ Integration with existing contracts
- ✅ Testing with real market conditions
- ✅ Before mainnet deployment

#### Alternative: Mainnet Forking with Foundry (Modern Standard)

While Hardhat is great for JavaScript developers, **Foundry (Anvil)** is the modern standard for Solidity engineers due to its extreme speed (written in Rust).

**Command to Fork:**
```bash
## Forks Ethereum Mainnet at block 17,000,000
anvil --fork-url https://eth-mainnet.alchemyapi.io/v2/YOUR_KEY --fork-block-number 17000000
```

**Why Foundry?**
- **Speed:** Forking and tests run 10-50x faster than Hardhat.
- **Trace:** Built-in call tracing (`-vvvv`) shows exactly where transactions failed.
- **Native Solidity:** Write tests in Solidity, not JavaScript.

---

#### Test 2: Fuzz Testing (Property-Based Testing)

**Status**: Advanced, for smart contracts  
**Cost**: Free (Foundry)  
**Website**: https://book.getfoundry.sh/

**What is it?**
Fuzz testing generates thousands of random inputs to find edge cases you didn't think of.

**Installation:**
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

**Example:**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract FuzzTest is Test {
    function testFuzz_Deposit(uint256 amount) public {
        vm.assume(amount > 0.01 ether);
        vm.assume(amount < 1000 ether);
        
        // Test will run with 10,000 random amounts
        // If any input breaks the contract, test fails
    }
}
```

**Run:**
```bash
forge test --fuzz-runs 10000
```

---

#### Test 3: Invariant Testing (Stateful Fuzzing)

**Status**: Professional / Audit-Ready  
**Cost**: Free (Foundry/Echidna)

**What is it?**
The "Silver Bullet" of DeFi security. While regular Fuzzing checks random inputs for *one* function, **Invariant Testing** checks a "Golden Rule" that must *always* be true after *sequences* of random transactions (e.g., Deposit -> Swap -> Withdraw -> Deposit).

**The "Golden Rule" (Invariant):**
*   "The Protocol's Total Assets must ALWAYS be greater than Total User Deposits."
*   "Users can NEVER withdraw more than they deposited."

**Example:**
```solidity
// Foundry Invariant Example
contract ProtocolSafetyCheck is StdInvariant, Test {
    function invariant_solvency() public {
        // This function executes after EVERY random transaction sequence
        // If this EVER fails, you have a critical bug.
        assertGe(vault.totalAssets(), vault.totalDebt()); 
    }
}
```

---

#### Test 4: Static Analysis with Slither

**Status**: Security essential  
**Cost**: Free  
**Website**: https://github.com/crytic/slither

**Installation:**
```bash
pip install slither-analyzer
```

**Usage:**
```bash
slither .
```

**When to use:**
- ✅ Before every deployment
- ✅ Before audits
- ✅ Continuous integration
- ✅ All smart contracts

---

### 6. SaaS & API Testing

#### Test 1: Load Testing with k6

**Status**: For APIs with many users  
**Cost**: Free (Open Source)  
**Website**: https://k6.io

**Installation:**
```bash
## macOS
brew install k6

## Windows
choco install k6

## Or download: https://github.com/grafana/k6/releases
```

**Example:**
```javascript
// load-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 200 },
  ],
};

export default function () {
  const res = http.get('https://api.yieldable.com/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

**Run:**
```bash
k6 run load-test.js
```

#### Test 2: Contract Testing (Backend/Frontend Sync)

**Status**: Professional Stability  
**Tool**: Pact (or Zod for runtime checks)

**What is it?**
Ensures the Backend API sends *exactly* what the Frontend expects. It prevents the common bug: "Backend changed the field name from `userId` to `id`, and now the Frontend is broken."

**How it works:**
1.  **Frontend** defines a "Contract" (I expect: `{ "id": string }`).
2.  **Backend** tests run against this Contract.
3.  If Backend changes to `{ "userId": string }`, their tests FAIL before deployment.

#### Test 3: Feature Flags ("Test in Production")

**Status**: Safe Deployment Strategy  
**Tool**: GrowthBook, LaunchDarkly, or simple Env Vars

**What is it?**
Deploying code that is "off" by default. You can enable it for specific users (e.g., "Internal Team" or "Beta Users") to test in the real production environment without risking the entire user base.

---

### 7. Implementation Guides

#### Quick Start: Add These 3 Tests Now

Based on your needs, here are the **3 tests to implement first**:

##### #1: Sentry (Error Monitoring)
**Time**: 10 minutes  
**Why**: Know when your app breaks in production  
**Steps**: Follow "Test 4: Error Monitoring with Sentry" above

##### #2: MSW (API Mocking)
**Time**: 10 minutes  
**Why**: Work offline, test error states  
**Steps**: Follow "Test 2: API Mocking with MSW" above

##### #3: Playwright (E2E Testing)
**Time**: 15 minutes  
**Why**: Ensure critical flows always work  
**Steps**: Follow "Test 3: End-to-End Testing with Playwright" above

#### For Your Trading Bot Specifically

##### Essential Tests:
1. **Mainnet Forking** (MUST HAVE)
   - Test trading strategies with real market data
   - No testnet deployment needed
   - Safe experimentation

2. **Fuzz Testing**
   - Test with random trade amounts
   - Find edge cases in your strategy

3. **Slither**
   - Security analysis for your contracts
   - Catch vulnerabilities before hackers do

---

### 8. Quick Reference: Testing Tools

#### Complete Tools Library

| Category | Tool | What It Does | Cost | Sign Up Link | Best For |
|----------|------|--------------|------|--------------|----------|
| **Unit Testing** | Jest | Tests functions/components | Free | Built-in | All projects |
| **E2E Web** | Playwright | Automates browser | Free | https://playwright.dev | Critical flows |
| **E2E Mobile** | Maestro | Mobile automation | Free | https://maestro.mobile.dev | React Native |
| **API Mocking** | MSW | Mocks API responses | Free | https://mswjs.io | Offline dev |
| **Error Tracking** | Sentry | Production errors | Free tier | https://sentry.io/signup/ | All production apps |
| **Visual Testing** | Storybook | Component development | Free | https://storybook.js.org | Component libraries |
| **Visual Testing** | Chromatic | UI regression | Free tier | https://www.chromatic.com | Open source projects |
| **Load Testing** | k6 | Simulate many users | Free | https://k6.io | Performance testing |
| **Smart Contracts** | Foundry | Solidity testing | Free | https://getfoundry.sh/ | DeFi protocols |
| **Smart Contracts** | Hardhat | Contract testing | Free | https://hardhat.org/ | General Solidity |
| **Security** | Slither | Vulnerability detection | Free | https://github.com/crytic/slither | All contracts |
| **Mainnet Fork** | Hardhat | Fork real blockchain | Free | https://hardhat.org/ | Testing with real data |
| **Mainnet RPC** | Alchemy | Access blockchain | Free tier | https://www.alchemy.com/ | Mainnet forking |
| **Mainnet RPC** | QuickNode | Access blockchain | Free tier | https://www.quicknode.com/ | Mainnet forking |

#### Free Tier Limits

| Service | Free Tier | Notes |
|---------|-----------|-------|
| **Sentry** | 5,000 errors/month | Perfect for small apps |
| **Alchemy** | 300M compute units | Enough for development |
| **QuickNode** | 50M credits | Good for testing |
| **Chromatic** | 5,000 snapshots | For private repos |
| **Chromatic** | Unlimited | For open source |
| **BrowserStack** | 100 min/month | Mobile testing |
| **Firebase Test Lab** | 100 min/day | Android testing |

---

### Summary: What to Implement

#### Recommended Roadmap for New Projects

**Week 1 (Foundation):**
- [ ] Sentry - Track production errors
- [ ] MSW - Mock APIs for offline development
- [ ] Playwright - Test critical user flows

**Week 2-4 (Expansion):**
- [ ] Mainnet Forking - Test with real blockchain data (if Web3)
- [ ] Slither - Security analysis for contracts (if Web3)
- [ ] Maestro - Mobile app testing (if Mobile)

**Month 2+ (Professional):**
- [ ] Chromatic/Lost Pixel - Visual regression testing
- [ ] k6 - Load testing
- [ ] Invariant Testing - For "Golden Rule" safety (if DeFi)

#### For Your Trading Bot (Special Case):

**Must Have:**
- [ ] Mainnet Forking - Test with real market data
- [ ] Slither - Security analysis
- [ ] Sentry - Error tracking

**Highly Recommended:**
- [ ] Fuzz Testing - Random input testing
- [ ] Playwright - Test bot UI/dashboard
- [ ] Unit Tests - Test calculation functions

---

### Resources

#### Documentation Links
- **Jest**: https://jestjs.io/docs/getting-started
- **Playwright**: https://playwright.dev/docs/intro
- **MSW**: https://mswjs.io/docs/
- **Sentry**: https://docs.sentry.io/
- **Foundry**: https://book.getfoundry.sh/
- **Hardhat**: https://hardhat.org/docs
- **Slither**: https://github.com/crytic/slither/wiki
- **k6**: https://k6.io/docs/
- **Maestro**: https://maestro.mobile.dev/

#### Learning Resources
- **Testing JavaScript**: https://testingjavascript.com/
- **Smart Contract Best Practices**: https://consensys.github.io/smart-contract-best-practices/
- **Solidity Patterns**: https://github.com/fravoll/solidity-patterns

---

*This document is a living guide. Update it as you implement new tests and discover new tools!*
