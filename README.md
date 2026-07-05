# FlowForm

**Build adaptive surveys, scored quizzes, and research questionnaires with version control, team access, and privacy-aware response storage.**

FlowForm is a modern survey platform for teams that need more than a static form. It helps users create branching forms that adapt in real time, publish stable survey versions, share public response links, and review submissions through a secure management dashboard.

Respondents only see the questions that are relevant to them. Survey creators get a structured workspace for building, publishing, distributing, and managing forms with confidence.

**Live site:** [flow-form.com.au](https://flow-form.com.au)
**Support:** [support@flow-form.com.au](mailto:support@flow-form.com.au)

---

## Why FlowForm

Most form tools are easy to start with but become difficult to trust as forms change, teams grow, or data becomes sensitive.

FlowForm is designed around reliability from the start:

* **Adaptive form experiences** — build surveys that branch based on respondent answers
* **Version-controlled publishing** — edit drafts safely and publish stable, immutable survey versions
* **Team-based access control** — manage project and survey permissions with role-based access
* **Privacy-conscious storage** — separate identifying application data from sensitive response payloads
* **Auditability** — keep responses tied to the exact survey version that collected them
* **Modern developer architecture** — OpenAPI-driven API contracts, generated frontend types, and a clean Flask service layer

FlowForm is built for use cases where structure, traceability, and confidence matter: research questionnaires, scored assessments, internal audits, onboarding forms, intake workflows, and decision-tree style surveys.

---

## Product overview

FlowForm is split into three main experiences.

### Public site

The public site provides the marketing, documentation, and public-facing entry point for FlowForm.

It is built with **Astro 6**, using a static-first architecture with React islands where interactivity is needed. This keeps the site fast, SEO-friendly, and simple to deploy.

### Studio

Studio is the authenticated management dashboard for survey creators and team members.

Users can manage:

* Projects
* Surveys
* Survey versions
* Visual survey building
* Conditional logic
* Public links
* Responses
* Project and survey access
* Members and roles
* Account settings

Studio is built with **React 19**, **TypeScript**, **Vite**, **TanStack Router**, **TanStack Query**, and **Tailwind v4**.

### Public form filler

The public form-filler experience lets respondents complete published surveys through shareable links without needing an account.

Interactive form rendering is handled by shared builder/runtime code from `@flowform/builder`, including the `FormFillerPage` React island embedded into the Astro public site.

---

## Core workflow

```text
Create project
  → Create survey
  → Build draft version
  → Add questions and conditional rules
  → Publish immutable version
  → Share public link
  → Collect responses
  → Review submissions in Studio
```

The key design principle is that live forms are not edited directly. Creators work on drafts, then publish stable versions when ready. Each response remains connected to the exact published version the respondent completed.

---

## Feature highlights

### Adaptive survey builder

FlowForm supports a visual builder for creating branching surveys and structured questionnaires.

Current question families include:

* Choice
* Multi-choice
* Field
* Rating
* Matching

Rule-based conditional logic allows forms to adapt as respondents answer, so unnecessary questions can be skipped and the experience stays focused.

### Versioned publishing

Survey versions can move through draft and published states. Published versions are treated as stable snapshots, protecting already-collected responses from later changes.

This makes FlowForm suitable for workflows where data integrity matters.

### Public links

Creators can distribute surveys through public links. Public links resolve to published survey versions, allowing respondents to complete forms without logging in.

### Response review

Submitted responses can be reviewed inside Studio. Core submission metadata is stored separately from raw response payloads to support privacy-focused data handling.

### Role-based access control

FlowForm includes project-level and survey-level role-based access control, making it suitable for teams where different users need different levels of access.

### OpenAPI-driven development

The backend generates an OpenAPI 3.1 spec at runtime. Frontend TypeScript types are generated from this spec using `openapi-typescript`, keeping the API contract consistent across backend and frontend code.

---

## Current build status

FlowForm already includes the major foundations of a production-style SaaS application.

### Public site

* Marketing and landing pages built with **Astro 6**
* Static-first architecture with React islands
* Public form-filler experience for published surveys
* `FormFillerPage` embedded from `@flowform/builder`

### Studio app

An authenticated React SPA for survey creators and team members, including:

* Project management
* Survey management
* Visual builder
* Survey versioning
* Access and public link management
* Survey members and roles
* Response viewing
* Account settings

### Backend API

A Flask REST API under `/api/v1/...`, including:

* Auth0 JWT authentication
* Project and survey RBAC
* Two-database design
* Pseudonymous respondent IDs
* Runtime OpenAPI 3.1 generation
* Centralised error handling
* Pydantic request/response validation

---

## Architecture overview

```text
FlowForm
├── Public site
│   ├── Astro 6
│   ├── Static marketing/docs pages
│   └── React islands for public form filling
│
├── Studio app
│   ├── React 19
│   ├── TypeScript
│   ├── Vite
│   ├── TanStack Router
│   ├── TanStack Query
│   └── Tailwind v4
│
├── Shared frontend packages
│   ├── @flowform/ui
│   ├── @flowform/styles
│   ├── @flowform/site-shell
│   └── @flowform/builder
│
└── Backend API
    ├── Flask 3
    ├── SQLAlchemy 2
    ├── Pydantic v2
    ├── Auth0 JWT validation
    ├── OpenAPI 3.1 generation
    ├── Core PostgreSQL database
    └── Response PostgreSQL database
```

---

## Repository structure

```text
FlowForm/
├── backend/                Flask API (Python 3.14+, uv)
└── frontend/               pnpm workspaces monorepo
    ├── apps/
    │   ├── studio-app/     Management dashboard
    │   └── public-site/    Marketing site + public form filler
    └── packages/
        ├── @flowform/ui           Shared UI components
        ├── @flowform/styles       Design tokens, Tailwind v4 config, fonts
        ├── @flowform/site-shell   Site header and navigation constants
        └── @flowform/builder      Survey editor and form-filler runtime
```

---

## Backend architecture

The backend is structured around a clean Flask service architecture.

```text
Route
  → validate request with Pydantic
  → call service
  → enforce domain rules and permissions
  → use repositories for database access
  → return ORM/domain result
  → serialize response with Pydantic
```

### Key backend patterns

* **Thin routes** — Flask routes handle HTTP concerns only
* **Pydantic boundary validation** — request and response schemas define the API contract
* **Service layer** — coordinates use cases, business rules, and cross-database workflows
* **Repository layer** — reusable database access logic
* **Domain rules** — reusable validation and business-state checks
* **Centralised error handling** — application, validation, HTTP, and unexpected errors become consistent JSON responses
* **Database error translation** — named constraints and integrity errors map to useful API errors

This keeps route files small and makes business logic easier to test, reuse, and reason about.

---

## Data and privacy model

FlowForm uses two PostgreSQL databases.

| Database   | Purpose                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------- |
| `core`     | Users, projects, surveys, versions, roles, links, permissions, subjects, and session metadata |
| `response` | Encrypted response envelopes and answer payloads only                                         |

The response database does not store real user IDs, project IDs, survey IDs, or plaintext question IDs. There are no cross-database SQL foreign keys — the two sides are linked only through HMAC-derived opaque locators computed from a versioned linkage secret:

```text
core.submission_sessions  →  session_locator  →  response.response_envelopes
core (question node)      →  answer_locator   →  response.response_answers
```

Answer payloads are also encrypted at rest using a per-survey KMS-wrapped branch key that locally wraps a per-session data encryption key (AES-256-GCM), so no plaintext answer is ever visible to the response database. See [docs/session-encryption/](docs/session-encryption/) for the full design.

Cross-database orchestration lives in the service layer. This keeps privacy-sensitive writes explicit and avoids hidden coupling between the two databases.

### Why this matters

This design makes FlowForm better suited for sensitive data collection because identifying application data and raw answers are not stored together by default, and even a full compromise of the response database exposes only encrypted, unlinkable blobs.

---

## Survey versioning model

Surveys are versioned so that edits do not accidentally rewrite history.

```text
Survey
  └── Survey Version
      ├── draft
      ├── published
      └── archived
```

A user edits a draft version. When ready, the draft is published as an immutable version. Public links point to published versions, and responses are recorded against the version that was active at the time.

This protects historical response data from becoming inconsistent when the survey changes later.

---

## Frontend architecture

The frontend is a pnpm workspaces monorepo split into apps and shared packages.

### Studio app

The Studio app is the authenticated management experience.

Core technologies:

* React 19
* TypeScript
* Vite 8
* TanStack Router v1
* TanStack Query v5
* Tailwind v4
* Auth0

### Public site

The public site is built with Astro 6.

It provides:

* Marketing pages
* Landing pages
* Public form-filler routes
* Static-first performance
* React islands for interactive form filling

### Shared packages

Shared frontend code is split into packages:

* `@flowform/ui` — reusable UI components
* `@flowform/styles` — design tokens, Tailwind config, and fonts
* `@flowform/site-shell` — shared site header and navigation constants
* `@flowform/builder` — survey builder and form-filler components

This keeps the product consistent across Studio, the public site, and the respondent experience.

---

## Tech stack

| Layer              | Technology                                                        |
| ------------------ | ----------------------------------------------------------------- |
| Backend            | Python 3.14+, Flask 3, SQLAlchemy 2, Pydantic v2                  |
| Backend auth       | Auth0, RS256 JWTs, JWKS verification, `@auth.require_auth(scope)` |
| Database           | PostgreSQL, split into `core` and `response` databases            |
| Public site        | Astro 6                                                           |
| Studio app         | React 19, TypeScript, Vite 8                                      |
| Routing            | TanStack Router v1                                                |
| Server state       | TanStack Query v5                                                 |
| Styling            | Tailwind v4, design tokens, `@flowform/styles`                    |
| Shared UI          | `@flowform/ui`                                                    |
| Builder/runtime    | `@flowform/builder`                                               |
| Package management | uv for backend, pnpm workspaces for frontend                      |
| API contract       | OpenAPI 3.1, `openapi-typescript`                                 |

---

## API and OpenAPI

The backend generates an OpenAPI 3.1 spec at runtime from Pydantic models and lightweight `@openapi_route` metadata on Flask view functions.

The decorator is documentation-only. It records metadata such as:

* Summary
* Tags
* Request model
* Response model
* Auth mode

The spec builder combines this registry with the live Flask URL map and serves:

* `/openapi.json` — raw JSON for tooling
* `/docs` — Swagger UI for browsing

All API errors use a shared response shape:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {}
}
```

Validation failures include Pydantic field errors under `details.errors[]`.

Frontend TypeScript types are generated from the spec with `openapi-typescript`, keeping the API contract as the single source of truth.

---

## CI

GitHub Actions runs on push and pull request to `main`.

The CI pipeline includes:

1. **Security checks** — backend dependency/security audit
2. **Backend tests** — pytest inside Docker with two real PostgreSQL databases
3. **Frontend build** — installs dependencies and builds both frontend apps
4. **Coverage artifact** — backend test coverage uploaded as an artifact

The backend tests use real databases rather than mocks, which gives stronger confidence in constraints, transactions, and cross-database logic.

---

## Development quick start

```bash
git clone https://github.com/Shayman-M-86/FlowForm.git
cd FlowForm
code .vscode/flowform.code-workspace
```

Allow automatic tasks when prompted, or press `Ctrl+Shift+B` to run the build task manually.

### Backend tests

Run tests inside Docker:

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "test_name"
```

### Frontend dev servers

```bash
cd frontend
corepack enable
pnpm install
pnpm run dev:studio   # Studio app — http://localhost:5174
pnpm run dev:site     # Public site — http://localhost:4321
```

---

## AI-assisted development

FlowForm uses AI-assisted development workflows to keep the growing codebase easier to navigate and maintain.

Claude Code is used as a primary development tool, supported by custom MCP servers, repo summarisation workflows, and project-specific agent skills.

### Custom MCP servers

Two project-local MCP servers live in `tools/mcp/` and are registered in `.mcp.json`.

#### `flowform-openapi`

Exposes the live backend OpenAPI spec to the AI agent.

This allows the agent to:

* Discover endpoints
* Inspect schemas
* Review documented errors
* Work from the current API contract instead of stale copies

It fetches `/openapi.json` from the running backend and authenticates through Auth0 Device Authorization Flow.

#### `flowform-repomap`

Supports iterative codebase summarisation.

It guides the agent through configured directories, saves summaries, and generates scoped rule files in `.claude/rules/repomap/` so relevant context loads only when needed.

### AI agent workflows

* **Feature development** — plan and implement backend/frontend changes against the current API contract
* **Repo summarisation** — keep directory-level summaries fresh across backend, frontend, tests, and shared packages
* **Wire-API skill** — sync OpenAPI changes into frontend `schema.ts`, `types.ts`, `requests.ts`, and `hooks.ts`
* **Code review** — `/code-review` skill runs multi-agent review on pull requests
* **Security review** — project-specific review of authentication, pseudonymity, and cross-database isolation
* **Browser verification** — Chrome DevTools MCP for manual UI checks

### Other tooling

* **ruff** — Python linting and formatting
* **pip-audit** — dependency vulnerability scanning in CI
* **Chrome DevTools MCP** — browser automation for UI verification

---

## Workspace

This repository is designed to be opened as a multi-root VS Code workspace.

```text
root       Entire repository
backend    Backend only
frontend   Frontend only
```

Open `.vscode/flowform.code-workspace` for full workspace support, including automatic tasks.

If automatic tasks were blocked:

```text
Ctrl+Shift+P → Tasks: Manage Automatic Tasks → Allow
```

---

## Project direction

The immediate product direction is to keep tightening the complete user journey:

```text
Create project
  → Create survey
  → Build and publish version
  → Share public link
  → Submit response
  → Review response in Studio
```

That vertical slice is the heart of FlowForm. Advanced branching, scoring, analytics, team workflows, and richer exports can continue to grow around it.
