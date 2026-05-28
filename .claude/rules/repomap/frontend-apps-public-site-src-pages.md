---
paths: frontend/apps/public-site/src/pages/**
---

# frontend/apps/public-site/src/pages/

_Last updated: 2026-05-27 by /repomap_

Contains the two Astro page entry points for the public-facing marketing site. `index.astro` is the full marketing homepage — it includes multiple feature sections (live builder demo via `NodePageIsland`, question types, adaptive logic, scoring/export, security, and a CTA) with Tailwind-styled layouts. `docs/[...slug].astro` is a static-path generator that pulls from an Astro content collection (`docs`), strips the `docs/` prefix from entry IDs, and renders each document inside a `DocsLayout`. All routing is file-based Astro convention; React islands are used only where interactivity is needed.
