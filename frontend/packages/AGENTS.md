# FlowForm Packages - Codex Guide

Shared workspace packages consumed by `studio-app` and `public-site`.
Changes here affect both apps - test in both before committing.

---

## Packages

| Package | Purpose |
|---|---|
| `@flowform/ui` | 18 shared UI components |
| `@flowform/styles` | Design tokens, Tailwind v4 config, font faces |
| `@flowform/site-shell` | SiteHeader component and nav constants |
| `@flowform/builder` | Survey editor (`NodePage`) and form filler (`FormFillerPage`) |

---

## How packages are consumed

Packages are consumed **as source** - there is no build or publish step.
Both apps resolve package imports to source files via:

1. **tsconfig path aliases** (`@flowform/ui` -> `../../packages/ui/src/index.tsx`)
2. **Vite `resolve.alias`** in each app's Vite / Astro config

This means changes to package source are reflected immediately in the dev
server without any rebuild step.

---

## Package exports

Each package exports from its `src/index.ts` (or `index.tsx`). CSS subpaths
are exported as separate alias entries (e.g. `@flowform/styles/tokens.css`).
When adding a new export, update both the source index and the alias entries
in `apps/studio-app/vite.config.ts` and `apps/public-site/astro.config.mjs`.

---

## `@flowform/ui` components

```text
Badge, Button, Card, DropdownMenu, ExpandableSelector, ExpandableTextArea,
Input, LargeInput, Modal, NumberStepper, NumberStepperGroup, Select,
Spinner, TabSelector, ThemeProvider, ThemeToggle, Toggle, Tooltip
```

Add new components under `packages/ui/src/components/ui/` and export from
`src/index.tsx`. Keep components generic and app-agnostic - no Studio- or
public-site-specific logic.

---

## `@flowform/styles` tokens

Design tokens are CSS custom properties in `src/tokens.css`. Naming pattern:

```css
--primary, --primary-hover, --primary-press, --primary-active
--accent, --accent-muted
--destructive, --destructive-foreground, --destructive-hover
--foreground, --muted-foreground, --background, --border, --ring
--radius, --font-sans, --font-serif, --font-mono
```

Light and dark theme values are set on `:root` with overrides in
`[data-theme="dark"]`. Always use token variables in components - never
hardcode colour values.

---

## `@flowform/builder`

Exports `NodePage` (survey editor) and `FormFillerPage` (end-user filler).
Both are full-page React components that expect to be wrapped in a Router
(see `NodePageIsland.tsx` in public-site for the pattern). CSS must be
imported separately via `@flowform/builder/node-page.css`.
