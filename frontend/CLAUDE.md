# FlowForm Frontend — Claude Code Guide

## What this is

The frontend monorepo for FlowForm. Contains two apps and shared packages.

## Apps

| App | Path | Purpose |
|---|---|---|
| `studio-app` | `apps/studio-app/` | Management dashboard (React 19 + Vite SPA) |
| `public-site` | `apps/public-site/` | Public-facing site and form renderer |

## Packages

| Package | Path | Purpose |
|---|---|---|
| `@flowform/ui` | `packages/ui/` | Shared UI component library |
| `@flowform/styles` | `packages/styles/` | Design tokens and Tailwind config |
| `@flowform/site-shell` | `packages/site-shell/` | SiteHeader and nav constants |
| `@flowform/builder` | `packages/builder/` | Survey/question builder |

---

## TODO: Add frontend-specific guidance here

- Node version / package manager
- How to run the dev servers
- How to build / publish packages
- Workspace dependency conventions
