# FlowForm Public Site - Codex Guide

The public-facing app. Handles the marketing site and the end-user survey
experience. Built with **Astro 6** - not a React SPA.

---

## Tech stack

- **Astro 6** - file-based routing, content collections, SSG/SSR
- **React 19** - used only for interactive islands via `client:*` directives
- **Tailwind v4** - via `@tailwindcss/vite` plugin
- **`@flowform/builder`** - `NodePage` (editor) and `FormFillerPage` (filler)
  are rendered as React islands inside Astro pages
- **`@flowform/ui`**, **`@flowform/styles`**, **`@flowform/site-shell`** -
  shared workspace packages, consumed as source (no build step needed)

---

## Commands

```bash
pnpm run astro dev      # dev server
pnpm run astro build    # production build
pnpm run astro preview  # preview built output
```

---

## Routing

Routing is **file-based** under `src/pages/`. Each `.astro` file is a route.

```text
src/pages/
├── index.astro              # / - marketing home
└── docs/[...slug].astro     # /docs/* - content collection
```

Do not use TanStack Router here - that is Studio-only. Dynamic segments use
Astro's `[param]` and `[...slug]` filename syntax.

---

## React islands

Interactive components are React components rendered with a `client:*`
directive in an `.astro` file. Example:

```astro
import { NodePageIsland } from "../components/NodePageIsland";
<NodePageIsland client:only="react" />
```

`NodePageIsland` wraps `NodePage` and `FormFillerPage` from `@flowform/builder`
in a `MemoryRouter` so the builder can do client-side navigation without
affecting Astro's routing.

Static Astro components (`.astro` files) do not need a `client:*` directive
and ship zero JS by default - keep components as `.astro` unless interactivity
is required.

---

## Vite / Astro config

`astro.config.mjs` resolves workspace packages as source via `resolve.alias`.
The order of alias entries matters - more specific paths (e.g.
`@flowform/styles/tokens.css`) must come before the package root alias.

The `@pinegrow/piny-astro` integration is a design tool plugin. Do not remove
or reorder it in the integrations array.

---

## Styles

- Tailwind v4 utility classes for layout and spacing
- Design tokens from `@flowform/styles/src/tokens.css` as CSS custom properties
  (`--primary`, `--accent`, `--foreground`, etc.)
- Import CSS subpaths where needed:
  - `@flowform/styles/tokens.css` - CSS variables only
  - `@flowform/styles/fonts.css` - Geist font face declarations
  - `@flowform/builder/node-page.css` - builder component styles
