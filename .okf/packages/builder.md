---
type: Package
title: "@flowform/builder"
description: Survey editor (NodePage) and end-user form filler (FormFillerPage), shared as source between Studio and the public site.
resource: frontend/packages/builder/
tags: [frontend, react, survey-builder]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Exports two full-page React components:

- `NodePage` — the visual survey editor
- `FormFillerPage` — the end-user survey-filling experience, rendering
  branching/conditional-logic surveys built against the
  [survey versioning model](/architecture/survey-versioning.md)

Both expect to be wrapped in a Router — [public-site](/apps/public-site.md)
does this via `NodePageIsland.tsx`, which wraps them in a `MemoryRouter` so
client-side navigation doesn't interfere with Astro routing. CSS must be
imported separately via `@flowform/builder/node-page.css`.

`FormFillerPage` has not yet been integrated into [Studio](/apps/studio-app.md);
today it is only embedded in the public site.

# Citations

[1] [frontend/packages/CLAUDE.md](../../frontend/packages/CLAUDE.md)
[2] [frontend/apps/public-site/CLAUDE.md — React islands](../../frontend/apps/public-site/CLAUDE.md)
