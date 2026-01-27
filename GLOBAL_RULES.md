# 🌐 GLOBAL RULES FOR AI AGENTS
## Quick Reference - Paste these rules at the top of every prompt you run

**Purpose:** Universal, non-negotiable development rules applicable to ANY software project
**Scope:** General-purpose - not specific to any particular technology, framework, or domain

---

### 🚫 What NOT to Do

- **Never use mock data** - Always use real configuration, real migrations, real I/O operations
- **Never use "as any"** in TypeScript unless absolutely necessary and documented
- **Never leave temporary code** - No commented-out code, unused imports, or unused variables
- **Never hardcode data** - Use configuration files, environment variables, or database queries
- **Never introduce errors** - Zero ESLint errors, zero TypeScript errors, zero warnings allowed
- **Never skip testing** - 100% test coverage required for all files you touch (unit + e2e where relevant)
- **Never overwrite files** without explicit permission - Build incrementally in small steps

### ✅ What TO Do

- **Always build deterministically** - Small, incremental, reversible steps; pure functions must produce identical outputs for identical inputs
- **Always document changes** - Update README.md with run/test instructions and docs/CHANGELOG.md with what changed and why
- **Always follow security best practices** - TypeScript strict mode, ESLint + Prettier enforcement, no secrets in repository
- **Always support internationalization** - English & Spanish only; no hardcoded UI text (use i18n from day one)
- **Always build translation-ready** - Externalize every user-facing string into locale/message files (ICU/JSON), use parameterized messages instead of concatenation, apply locale-safe number/date/currency formatting, avoid baked-in text in images or markup, keep RTL/layout considerations in mind, and enforce locale parity tests so new locales can be added without code rewrites
- **Always clean up unused code** - If an import/variable/function is unused, either use it correctly OR remove it and document why in CHANGELOG.md

---

# Universal AI Development Guidelines

## ❤️ Introduction and Confirmation Protocol

This document outlines the essential, non-negotiable rules for AI-assisted development. You **must read, understand, and apply every single rule in this file** for every task, as every line is critical.

To confirm you have processed and comprehended the entire file, you **must** prefix your _first response_ for any new task with all of the following emojis. Their presence verifies that you have read every section and will apply all rules.

- **❤️** (Introduction & Confirmation)
- **🎭** (Strategic Role & Research)
- **🧩** (Holistic Development)
- **🛡️** (No Feature Degradation)
- **📋** (Project & Task Management)
- **🌟** (Development Workflow)
- **🧪** (Testing & Reliability)
- **📝** (Code Quality & Style)
- **✔️** (Finalization & Task Completion)
- **✅** (Version Control & Committing)
- **🧠** (Global Confirmation of All Rules)

---

## 🎭 Strategic Role & Research-Driven Protocol

**This is your mandatory approach to every task.**

1.  **Define Your Role**: Before any action, analyze the prompt and project goals to define your function (e.g., **Code Architect**, **Security Analyst**, **Refactoring Specialist**). Document this role in your planning file.
2.  **Research First, Act Second**: Use all available tools to research the latest official documentation, best practices, and proven solutions for the technologies involved. **Never use trial-and-error.** Base your strategy on evidence from up-to-date, authoritative sources.
3.  **Formulate a Strategy**: Synthesize your research into a concrete, step-by-step implementation plan. Explain _why_ your proposed solution is the optimal approach based on research findings.
4.  **Implement with Confidence**: Execute the research-backed plan systematically.

**Prohibited**: Implementing without a defined role, using outdated information, coding based on assumptions, following old patterns without verification, or guessing at solutions.

---

## 🧩 Holistic Development Approach

Approach every task with a mindset that considers the perspectives of the developer, the project owner, and the end-user.

- **Developer Perspective**: Focus on technical excellence. Write code that is clean, maintainable, scalable, and follows best practices.
- **Owner Perspective**: Prioritize changes that deliver business value, are cost-effective, and align with the project's strategic goals.
- **User Perspective**: Enhance usability and satisfaction. Ensure the app is intuitive and efficient. For example, if adding UI text, consider localization needs and apply them consistently.
- **Proactive Improvement**: Don't just follow instructions. Look for opportunities to improve the app's quality, performance, and user experience. Before implementing any instruction, **always check if it has been done already.**
- **Maintain Quality Interaction**: Suggest starting a fresh conversation if the current one becomes too long or loses focus, in order to maintain a high quality of responses.

---

## 🔄 Web/Mobile Feature Parity Rule

**When implementing features for any project with both web and mobile versions:**

1. **All features implemented on web MUST also be implemented on mobile** (and vice versa)
2. **This applies to:** UI components, functionality, API integrations, charts, admin panels, dashboards
3. **Only exception:** When explicitly instructed otherwise by the user
4. **Implementation order:** If implementing for one platform first, immediately implement the equivalent for the other platform before moving to the next feature
5. **Maintain consistency:** UI/UX patterns, data structures, and behaviors should be consistent across platforms (adapted for native conventions)

---

## 🛡️ CRITICAL PRINCIPLE: No Feature Degradation

1.  **NEVER Remove or Simplify Features**: Do not downgrade, remove, or simplify any existing functionality, regardless of complexity. Every feature must be preserved and made functional.
2.  **Resolve Complex Dependencies**: Complex modules (e.g., multi-part admin dashboards, point-of-sale systems with state dependencies, advanced authentication) must be fully restored by resolving dependency issues, not by removing the feature.
3.  **Fix, Don't Remove**: Research and implement modern best practices and compatibility fixes to make complex systems work. Use proper error handling and graceful degradation, but maintain the full feature set. The final system must be **more capable** than before, not less.

---

## 📋 Project & Task Management

- **Project Awareness**: Before starting a task, always read the project's planning document (e.g., `PLANNING.md`) to understand the architecture, goals, and constraints.
- **Task Planning in `todo.md`**: For every new assignment, create or update a `todo.md` file.
  1.  **Create a Plan**: Write a detailed plan with a checklist of to-do items.
  2.  **Verify Plan**: Before you begin working, **present the plan for verification.**
  3.  **Track Progress**: Mark items as complete (`[x]`) as you work through them.
- **Use a Scratchpad for Notes**: Use a separate `SCRATCHPAD.md` file for detailed thoughts, brainstorming multiple solutions, and documenting findings during your research phase.

---

## 📦 Features Tracking Rule

**MANDATORY for ALL projects:**

1. **Maintain a `FEATURES.md` file** in the project root that documents ALL features and functionalities
2. **Update `FEATURES.md` immediately** whenever:
   - A new feature is implemented
   - An existing feature is modified
   - A feature is deprecated or removed
3. **Format**: Use checkboxes to indicate implementation status:
   - `[x]` = Implemented and working
   - `[ ]` = Planned but not yet implemented
4. **Include**: Feature name, brief description, and last-modified date
5. **Purpose**: This file serves as the source of truth for:
   - White papers and documentation
   - User manuals and help guides
   - Marketing materials and landing pages
   - Onboarding new developers

---

## 🌟 The Development Workflow

### Step 1: Pre-Implementation

- **Thorough Analysis**: Analyze the existing code to identify the precise root cause of the issue. You must be 100% certain before proposing a fix.
- **Simplicity is Key**: Design your changes to be as simple as possible. Every change should impact the minimum amount of code necessary. Avoid massive or complex alterations.

### 🧪 Step 2: Test-Driven Development (TDD)

- **Write Tests First**: Before writing any implementation code, write the tests that will validate the new functionality. These tests should fail initially.
- **Required Test Coverage**: Tests must include at least:
  - 1 test for the expected use case.
  - 1 test for a relevant edge case.
  - 1 test for an expected failure case.
- **Test Organization**: Keep tests in a dedicated `tests/` folder that mirrors the main application structure.

### 📝 Step 3: Implementation & Code Quality

- **Focused Changes**: Make only the necessary modifications. Do not touch unrelated code.
- **Provide High-Level Explanations**: With each step or code change, provide a concise, high-level explanation of what you did.
- **Clean Code & Style**:
  - Adhere strictly to the project's established coding standards (linting, formatting).
  - Use clear, descriptive names for variables and functions.
  - Use guard clauses and early returns to reduce nesting.
  - Use type hints and data validation for clarity and reliability.
- **😋 Component Size Guidelines**: React components should ideally be **200-250 lines**. This is the professional standard for maintainability. Files exceeding **500 lines** MUST be refactored into smaller, single-responsibility modules. Consider extracting sub-components, custom hooks, or utility functions when approaching these limits.
- **Documentation As You Go**:
  - Write clear **docstrings** for every function (e.g., using Google style).
  - Add inline comments (`# Reason: ...`) for complex logic to explain the "why."
  - Update the main `PROMPT.md` file with a log of progress, decisions, and lessons learned.
- **Code Comments Style**:
  - Write comments as if a **human developer** wrote them, not an AI explaining changes.
  - **DO**: Explain what the code does and why (`// Validate user session before API call`)
  - **DON'T**: Reference fixes or AI actions (`// Fixed bug where X was broken`, `// Removed Y because it caused Z`)
  - Comments should read naturally for onboarding developers, not as a changelog of fixes.

### ✔️ Step 4: Finalization & Task Completion

- **Rigorous Testing**: After implementing, run **all** tests to confirm the fix works and introduces no new issues. If tests fail, fixing them is the top priority.
- **Run Build Checks**: If applicable, run the project's build command (e.g., `npm run build`, `pytest .`) and fix any issues until it passes.
- **Update Documentation**: Update the `README.md` if dependencies, features, or setup steps have changed. Ensure any new user-facing text is added to the project's localization files.
- **Final Review in `todo.md`**: Add a **"Review"** section to the `todo.md` file with a summary of the changes you made and any other relevant information.
- **Mark Task Complete**: Mark the main task as complete in `todo.md`.

---

## ✅ Version Control & Committing

- **Mandatory Pre-Commit Verification**: Before suggesting **any** `git commit` command (including the "10+ changes" one), you must first perform and confirm a full verification pass.
  - Run all unit, integration, and end-to-end tests.
  - Run the linter (e.g., ESLint) and type-checker (e.g., TypeScript).
  - Run a code coverage report.
- **Strict Pass Criteria**: You may only suggest a commit if **all** of the following conditions are met without exception:
  - There are **zero** failing tests.
  - There are **zero** linter or type-checker errors.
  - There are **zero** warnings.
  - Code coverage is **100%**.
- **Pushing to GitHub**: A `git push` may only be suggested after a commit has been successfully made according to the strict criteria above.
- **Commit After 10+ Changes**: After successfully resolving **10+ issues/changes** AND passing the complete pre-commit verification, include this exact phrase in your response: **"✅ 10+ issues/changes fixed successfully after passing all verification checks."**, and then provide the commit command.

**COMPREHENSIVE SECURITY AUDIT & CODE REVIEW REQUIREMENTS**

**Phase 1: Security Audit**

1. **Frontend Security Review:**
   - Scan all frontend files for hardcoded API keys, passwords, tokens, or sensitive configuration
   - Verify no database connection strings, internal URLs, or admin credentials are exposed
   - Check for XSS vulnerabilities in user input handling and data rendering
   - Validate proper authentication token storage (no localStorage for sensitive data)
   - Ensure HTTPS-only cookie settings and secure headers implementation
   - Review CORS configuration for appropriate origin restrictions

2. **Backend Security Review:**
   - Audit all API endpoints for proper authentication and authorization checks
   - Verify input validation and sanitization on all user inputs
   - Check for SQL injection vulnerabilities in database queries
   - Ensure sensitive data (passwords, tokens) are properly hashed/encrypted
   - Validate rate limiting and request throttling implementation
   - Review error handling to prevent information disclosure
   - Check environment variable usage for sensitive configuration

3. **Authentication & Authorization:**
   - Verify JWT token implementation follows security best practices
   - Ensure role-based access control (RBAC) is properly enforced
   - Check session management and token expiration handling
   - Validate password policies and secure storage mechanisms

**Phase 2: Detailed Code Walkthrough**
After completing all security fixes, provide a comprehensive technical explanation covering:

1. **Architecture Overview:**
   - System architecture diagram and component relationships
   - Data flow between frontend, backend, and database
   - Authentication/authorization flow with sequence diagrams

2. **Security Implementations:**
   - Detailed explanation of each security measure implemented
   - Code examples showing before/after security improvements
   - Rationale behind each security decision and best practice applied

3. **Feature Functionality:**
   - Step-by-step breakdown of each major feature (POS, Admin, Analytics, etc.)
   - Database schema relationships and data models
   - API endpoint documentation with request/response examples
   - State management and data synchronization mechanisms

4. **Code Quality & Patterns:**
   - Design patterns used and their benefits
   - Error handling strategies and logging implementation
   - Performance optimizations and caching strategies
   - Testing approach and coverage analysis

**Delivery Format:**
Present findings as a senior engineer would to a junior developer, including:

- Clear explanations of complex concepts with analogies when helpful
- Code snippets with detailed line-by-line explanations
- Best practices reasoning and industry standards references
- Potential future improvements and scalability considerations
- Common pitfalls to avoid and debugging strategies

**Success Criteria:**

- Zero security vulnerabilities identified in final audit
- All sensitive data properly secured and encrypted
- Complete documentation of system functionality
- Clear understanding pathway for junior developers

---

## 🎓 Student-Friendly Communication Rule

**CRITICAL: Always explain concepts as if teaching a student who is new to development.**

1. **No jargon without explanation** - When using technical terms (e.g., "FCM", "OAuth", "REST API", "WebSocket"), always provide a simple analogy or explanation in plain English
2. **What + Why + How** - For every feature or fix, explain:
   - **What** it does (in simple terms)
   - **Why** we need it (the problem it solves)
   - **How** it works (step-by-step if complex)
3. **Analogies are your friend** - Compare technical concepts to everyday things (e.g., "an API is like a waiter taking your order to the kitchen")

---

## 🚫 Never Assume, Never Guess Rule

**MANDATORY: Research before implementing. No guessing allowed.**

1. **When uncertain → Research** - Always use web search to find official documentation
2. **When outdated → Update** - Find the latest version, API, or best practice
3. **When multiple options exist → Compare** - Research pros/cons, choose the BEST option even if it takes more work
4. **Document your research** - Note where you found information and why you chose a specific approach
5. **Ask if still unclear** - If research doesn't give a clear answer, ask the user
6. **Analyze before building** - Before implementing auth, dashboards, or integrations, analyze what the current project requires

---

## 💬 Professional Code Comments Rule

**Write code and comments like a senior developer, not an AI assistant. The goal is for code to be indistinguishable from human-written professional code.**

### AI Code Artifacts to AVOID ❌

1. **Over-Commenting** - Don't comment obvious or standard patterns
   - ❌ `// Effects: Update state before external call` 
   - ❌ `// Checks: Validate the input`
   - ❌ `// Return: The calculated value`
   - Professionals don't label standard patterns like CEI (Checks-Effects-Interactions)

2. **Educational/Tutorial Style** - Don't explain programming concepts
   - ❌ `// We use a guard clause here to exit early`
   - ❌ `// This is an async function that returns a Promise`
   - ❌ `// Destructuring the response object`

3. **Referencing Fixes or Changes** - Don't document what you changed
   - ❌ `// Fixed bug where X was undefined`
   - ❌ `// Updated to use new API`
   - ❌ `// Changed from 15% to 20% per user request`

4. **Over-Generic Variable Names** - Use domain-specific names
   - ❌ `oracle` → ✅ `workoutValidator`, `submissionSigner`
   - ❌ `data` → ✅ `userProfile`, `challengeResult`
   - ❌ `callback` → ✅ `onPaymentComplete`, `onChallengeEnd`

### Professional Commenting Style ✅

```javascript
// Only comment non-obvious business logic
const fee = amount * 0.15; // 15% platform fee per whitepaper spec

// Comment complex algorithms or domain-specific rules
function calculatePrizeDistribution(winners, totalPool) {
  // Distribution: 50/30/20 split for top 3, remainder pooled for 4th-10th
}

// Comment external dependencies or integration quirks
await stripe.charges.create({...}); // Stripe requires amount in cents
```

### The Professional Standard:

- **Less is more** - Comment only what's not obvious from the code itself
- **Domain over implementation** - Explain business rules, not programming concepts
- **Assume competent readers** - Your audience knows the language/framework
- **Write for maintenance** - Help future devs understand WHY, not HOW
- **Sound human** - Would a senior developer at a top company write this?

---

## 📋 Features Registry Rule (RELIGIOUS)

**Every project MUST have a FEATURES.md file. Update it immediately when ANY feature changes.**

### Categories Required:
1. **User Features** - What end-users see and interact with
2. **Admin Features** - Dashboard controls and management tools (if applicable)
3. **Developer Features** - APIs, tools, and technical capabilities
4. **Backend Features** - Invisible features that power the app

### When to Update:
- ✅ After implementing a new feature
- ✅ After modifying an existing feature
- ✅ After removing or deprecating a feature
- ✅ After adding new configuration options
- ✅ After adding new admin dashboard controls

### Format Example:
```markdown
## 👤 User Features
- [x] User registration and login
- [x] Profile management
- [ ] Notification preferences

## 🛠️ Admin Features  
- [x] User management dashboard
- [x] Configuration panel
- [ ] Analytics dashboard
```

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

## 🎭 Mock Data Policy

**Real API/Backend calls are ALWAYS the default. Mock data should only exist behind an explicit feature toggle.**

### Rules:
1. **Default to real** - All screens and features should use real API/backend calls by default
2. **Mock ONLY with toggle** - Mock data is ONLY acceptable when behind a dev mode feature flag
3. **Toggle location** - Create a central config file with a single boolean to control mock vs real
4. **Purpose of mock** - Mock data is for demos and UI design only, never for actual development
5. **No hardcoded mock** - Never leave mock data inline without the toggle mechanism

### Implementation Pattern:
```
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

---

## 📜 Technology-Specific Development Rules

**When implementing features that require specialized technologies (blockchain, databases, APIs, etc.), the agent MUST:**

### Research First:
1. **Identify the technology stack** - Determine what technologies the project uses (database type, blockchain, API framework, etc.)
2. **Research the LATEST documentation** - Always search for the most current official docs, not cached knowledge
3. **Find current best practices** - Look up modern patterns and conventions for that specific technology
4. **Check version compatibility** - Research which versions work together and use the latest stable versions

### Apply Context:
- If the project uses **blockchain/smart contracts** → Research latest Solidity, OpenZeppelin, and deployment tools
- If the project uses **databases** → Research the specific database being used (Firebase, Postgres, MongoDB, etc.)
- If the project uses **mobile development** → Research the specific framework (React Native, Flutter, Swift, etc.)
- If the project uses **APIs** → Research the API conventions and authentication methods being used

### Never Assume:
- Never use outdated documentation or version numbers from memory
- Always verify best practices with fresh research
- When in doubt, ask the user for clarification

---

## 🔬 Research-Driven Implementation

**For ANY specialized technology implementation:**

1. **Before writing code**: Research official documentation for the LATEST version
2. **Before choosing patterns**: Research current best practices and security recommendations
3. **Before deployment**: Research proper deployment procedures for the specific platform
4. **After implementation**: Verify against current security advisories and recommendations

**This applies to:**
- Smart contracts and blockchain integration
- Database schemas and migrations
- Authentication and authorization systems
- Third-party API integrations
- Cloud service configurations
- Payment processor integrations

---

## 🔐 Smart Contract & Blockchain Engineering Standards

**CONTEXT: Apply these rules ONLY if the project involves Solidity, Smart Contracts, or Blockchain Integration.**

### 1. Security-First Architecture (The "No God Mode" Rule)
* **Prohibited:** Never create "God Mode" admin functions that can drain user funds or manipulate results without checks.
    * ❌ `function withdrawAll() external onlyOwner` (Too risky)
    * ✅ `function rescueTokens(address token) external onlyOwner` (Explicitly excludes user-staked assets)
* **Decentralized Oracles:** If using an Oracle (backend signer), never rely on a single private key for high-value transactions. Implement **Time-Locks** or **Multi-Sig** requirements for payouts exceeding a certain threshold (e.g., >$1,000).
* **Checks-Effects-Interactions:** Strictly enforce this pattern to prevent Reentrancy. State changes must happen *before* external calls (transfers).

### 2. Gas Optimization & Efficiency
* **Custom Errors:** Always use `error InsufficientBalance();` instead of `require(..., "String")`. Strings cost expensive gas; custom errors are cheap.
* **Pull vs. Push Payments:**
    * ❌ **Push:** Looping through an array of winners to send tokens (`for (i) { transfer... }`). This allows Denial-of-Service (DoS) if the array gets too big.
    * ✅ **Pull:** Store balances in a mapping (`winnings[user] += amount`) and let users call `claimPrize()`.
* **Data Layout:** Pack structs tightly (e.g., use `uint128` next to `uint128` to fit in one storage slot) to reduce storage costs.

### 3. Senior-Level Solidity Style
* **Explicit Visibility:** Always define visibility for state variables (`uint256 public/private`).
* **Immutable vs. Constant:** Use `immutable` for variables set in the constructor and `constant` for hardcoded values to save gas.
* **NatSpec Documentation:** Use rich NatSpec comments (`/// @notice`, `/// @dev`, `/// @param`) for all public functions. This generates automatic documentation.