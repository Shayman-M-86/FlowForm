---
paths: frontend/packages/**
---

# frontend/packages/

_Last updated: 2026-05-27 by /repomap_

A monorepo of four shared internal packages consumed as source (no build/publish step) by both apps via tsconfig path aliases and Vite `resolve.alias`. `@flowform/ui` provides 18 generic, app-agnostic React UI components (Button, Modal, TabSelector, etc.) exported from `src/index.tsx`. `@flowform/styles` holds design tokens as CSS custom properties in `src/tokens.css` (light/dark theme, semantic colour variables, typography) plus Tailwind v4 config and font faces. `@flowform/site-shell` exports the `SiteHeader` component and nav constants used across both apps. `@flowform/builder` exports the full-page `NodePage` (survey editor) and `FormFillerPage` (end-user form filler) React components, each requiring CSS imported separately.
