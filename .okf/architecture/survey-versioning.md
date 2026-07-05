---
type: Architecture Decision
title: Survey versioning model
description: Surveys are edited as drafts and published as immutable versions so historical responses stay consistent.
tags: [backend, versioning, surveys]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

```text
Survey
  └── Survey Version
      ├── draft
      ├── published
      └── archived
```

A user edits a draft version. When ready, the draft is published as an
immutable version. [Public links](/architecture/openapi-contract.md) point to
published versions, and responses are recorded against the version that was
active at the time of submission.

Live forms are never edited directly — this is the core design principle
behind the [two-database privacy model](/architecture/two-database-model.md)
and the overall [core workflow](/index.md).

# Why this matters

This protects historical response data from becoming inconsistent when a
survey's structure changes later, and keeps each response auditable against
the exact version a respondent completed.

# Citations

[1] [Root CLAUDE.md — Survey versioning model](../../CLAUDE.md)
