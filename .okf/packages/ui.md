---
type: Package
title: "@flowform/ui"
description: Shared library of 18 generic, app-agnostic React UI components consumed as source by both frontend apps.
resource: frontend/packages/ui/
tags: [frontend, react, components]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Exports from `src/index.tsx`:

```text
Badge, Button, Card, DropdownMenu, ExpandableSelector, ExpandableTextArea,
Input, LargeInput, Modal, NumberStepper, NumberStepperGroup, Select,
Spinner, TabSelector, ThemeProvider, ThemeToggle, Toggle, Tooltip
```

New components go under `packages/ui/src/components/ui/` and must be
exported from `src/index.tsx`. Components must stay generic and
app-agnostic — no [Studio](/apps/studio-app.md)- or
[public-site](/apps/public-site.md)-specific logic.

Both frontend apps prefer `@flowform/ui` components over raw HTML
equivalents (a hard rule in Studio).

# Consumption

Consumed as source (no build/publish step) via tsconfig path aliases and
Vite `resolve.alias` in each app's config.

# Citations

[1] [frontend/packages/CLAUDE.md](../../frontend/packages/CLAUDE.md)
[2] [.claude/rules/repomap/frontend-packages.md](../../.claude/rules/repomap/frontend-packages.md)
