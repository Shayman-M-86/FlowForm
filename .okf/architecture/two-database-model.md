---
type: Architecture Decision
title: Two-database privacy model
description: FlowForm splits data across a `core` and a `response` PostgreSQL database to keep identifying data separate from raw answers.
tags: [backend, privacy, database, architecture]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

FlowForm uses two PostgreSQL databases instead of one:

| Database   | Purpose                                                                                |
|------------|-----------------------------------------------------------------------------------------|
| `core`     | Users, projects, surveys, versions, roles, links, permissions, and submission metadata |
| `response` | Raw response payloads and answer data                                                  |

The `response` database never stores a real `user_id` — only a stable
pseudonymous UUID. The two databases are linked only by a shared identifier:

```text
core.survey_submissions.id
  ↔ response.submissions.core_submission_id
```

Cross-database orchestration lives exclusively in the [service layer](/backend/services.md)
— never in [repositories](/backend/repositories.md) or [routes](/backend/api-v1.md). This keeps
privacy-sensitive writes explicit and avoids hidden coupling between the two
databases.

# Why this matters

Identifying application data and raw survey answers are not stored together
by default, which makes FlowForm better suited to sensitive data collection
(research questionnaires, audits, intake forms).

# Citations

[1] [Root CLAUDE.md — Data and privacy model](../../CLAUDE.md)
[2] [backend/CLAUDE.md](../../backend/CLAUDE.md)
