# FlowForm Frontend — Claude Code Guide

The frontend is a pnpm workspaces monorepo with two apps and five shared packages.

---

## Apps

| App | Path | Purpose |
| --- | --- | --- |
| `studio-app` | `apps/studio-app/` | Admin dashboard — React 19 + Vite SPA, port 5174 |
| `public-site` | `apps/public-site/` | Marketing site + form-filler — Astro 6 + React islands |

## Packages

| Package | Path | Purpose |
| --- | --- | --- |
| `@flowform/ui` | `packages/ui/` | Shared UI component library |
| `@flowform/styles` | `packages/styles/` | Design tokens and Tailwind v4 config |
| `@flowform/site-shell` | `packages/site-shell/` | SiteHeader and nav constants |
| `@flowform/builder` | `packages/builder/` | Survey/question builder widget |

---

## Commands

Run from `frontend/`:

```bash
pnpm run dev:studio         # Studio dev server on :5174
pnpm run dev:site           # Public site dev server
pnpm run build:studio       # Production build for Studio
pnpm run build:site         # Production build for public site
```

Run from the app directory directly:

```bash
# Studio
pnpm run routes             # Regenerate TanStack Router routeTree.gen.ts
pnpm run lint               # ESLint

# Public site
pnpm run astro dev
pnpm run astro build
```

---

## Discovering the API

The backend exposes its full REST surface — endpoints, request bodies,
response payloads, error codes, and examples — through an **OpenAPI MCP
tool** (`flowform-openapi`). Treat it as the source of truth when wiring up
API hooks, defining response types, or handling errors.

Use the MCP operations rather than greping for existing handlers or
guessing the shape:

- `list_operations` — every endpoint, grouped and tagged
- `find_operations` — keyword / path search when you know roughly what you want
- `describe_schema` — full request/response schema for a specific operation, including the unified `ErrorResponse` shape used by every error

Why this matters:

- Response types in `studio-app/src/api/types.ts` must match the backend
  exactly. The MCP tool gives you the authoritative shape; deriving it
  from another component's usage risks copying a stale type.
- The backend uses a single `ErrorResponse` shape (`{code, message, details?}`)
  everywhere, with `details.errors[]` carrying Pydantic field failures on
  422s. New error-handling code should consume that shape — confirm via
  `describe_schema` before branching on response keys.
- New backend endpoints are auto-documented; if you cannot find an
  operation in the MCP tool, it does not exist yet and frontend work
  should not assume it.

Swagger UI for the same spec is available at `<backend>/docs` and the raw
JSON at `<backend>/openapi.json` for human browsing.

---

## Sub-guides

| Area | Guide |
| --- | --- |
| Studio app | [apps/studio-app/CLAUDE.md](apps/studio-app/CLAUDE.md) |
| Public site | [apps/public-site/CLAUDE.md](apps/public-site/CLAUDE.md) |
| Shared packages | [packages/CLAUDE.md](packages/CLAUDE.md) |

---

## Key conventions

- Package manager: **pnpm** (native workspaces via `pnpm-workspace.yaml`) — do not use npm or yarn
- Dependency freshness gate: `minimumReleaseAge: 10080` in `pnpm-workspace.yaml` enforces a 7-day release age before new package versions can install
- TypeScript strict mode throughout; `noUnusedLocals` and `noUnusedParameters` enforced
- Packages are consumed as **source** via tsconfig path aliases and Vite resolve.alias —
  there is no build/publish step to run when editing a package locally
- Always prefer `@flowform/ui` components over raw HTML equivalents
- Design tokens live in `@flowform/styles/src/tokens.css` as CSS custom properties
