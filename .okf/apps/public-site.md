---
type: Service
title: Public site
description: The Astro 6 marketing site and respondent-facing form-filler experience, using React islands for interactivity.
resource: frontend/apps/public-site/
tags: [frontend, astro, public-site]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

The public-facing app — marketing pages, docs, and the end-user survey
experience. Built with Astro 6, not a React SPA. Routing is file-based
under `src/pages/`; each `.astro` file is a route. Do not use TanStack
Router here — that is [Studio](/apps/studio-app.md)-only.

`src/pages/index.astro` is the full marketing homepage, including a live
builder demo (`NodePageIsland`), question-type showcase, adaptive-logic,
scoring/export, and security sections. `src/pages/docs/[...slug].astro` is a
static-path generator pulling from an Astro content collection.

# React islands

Interactive components are React components rendered with a `client:*`
directive inside an `.astro` file, e.g. `<NodePageIsland client:only="react" />`.
`NodePageIsland` wraps `NodePage` and `FormFillerPage` from
[`@flowform/builder`](/packages/builder.md) in a `MemoryRouter` so the
builder can navigate client-side without affecting Astro's own routing.
Static `.astro` components ship zero JS and should be preferred unless
interactivity is required.

# Config notes

`astro.config.mjs` resolves workspace packages as source via
`resolve.alias`; more specific aliases (e.g. `@flowform/styles/tokens.css`)
must be listed before the package-root alias. The `@pinegrow/piny-astro`
integration is a design-tool plugin — do not remove or reorder it.

# Citations

[1] [frontend/apps/public-site/CLAUDE.md](../../frontend/apps/public-site/CLAUDE.md)
[2] [.claude/rules/repomap/frontend-apps-public-site-src-pages.md](../../.claude/rules/repomap/frontend-apps-public-site-src-pages.md)
