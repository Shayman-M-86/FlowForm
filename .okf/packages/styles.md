---
type: Package
title: "@flowform/styles"
description: Design tokens (CSS custom properties), Tailwind v4 config, and font faces shared by both frontend apps.
resource: frontend/packages/styles/
tags: [frontend, design-tokens, tailwind]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Design tokens live in `src/tokens.css` as CSS custom properties, with light
theme on `:root` and dark-theme overrides under `[data-theme="dark"]`:

```css
--primary, --primary-hover, --primary-press, --primary-active
--accent, --accent-muted
--destructive, --destructive-foreground, --destructive-hover
--foreground, --muted-foreground, --background, --border, --ring
--radius, --font-sans, --font-serif, --font-mono
```

Always use token variables in components — never hardcode color values (a
hard rule in [Studio](/apps/studio-app.md)).

# CSS subpaths

- `@flowform/styles/tokens.css` — CSS variables only
- `@flowform/styles/fonts.css` — Geist font face declarations

# Citations

[1] [frontend/packages/CLAUDE.md](../../frontend/packages/CLAUDE.md)
