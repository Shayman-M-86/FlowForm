# FlowForm Frontend — Claude Code Guide

The frontend is an npm workspaces monorepo with two apps and four shared packages.

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
npm run dev:studio          # Studio dev server on :5174
npm run dev:site            # Public site dev server
npm run build:studio        # Production build for Studio
npm run build:site          # Production build for public site
```

Run from the app directory directly:

```bash
# Studio
npm run routes              # Regenerate TanStack Router routeTree.gen.ts
npm run lint                # ESLint

# Public site
npm run astro dev
npm run astro build
```

---

## Sub-guides

| Area | Guide |
| --- | --- |
| Studio app | [apps/studio-app/CLAUDE.md](apps/studio-app/CLAUDE.md) |
| Public site | [apps/public-site/CLAUDE.md](apps/public-site/CLAUDE.md) |
| Shared packages | [packages/CLAUDE.md](packages/CLAUDE.md) |

---

## Key conventions

- Package manager: **npm** (native workspaces) — do not use pnpm or yarn
- TypeScript strict mode throughout; `noUnusedLocals` and `noUnusedParameters` enforced
- Packages are consumed as **source** via tsconfig path aliases and Vite resolve.alias —
  there is no build/publish step to run when editing a package locally
- Always prefer `@flowform/ui` components over raw HTML equivalents
- Design tokens live in `@flowform/styles/src/tokens.css` as CSS custom properties
