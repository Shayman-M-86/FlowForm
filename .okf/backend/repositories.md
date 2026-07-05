---
type: Service
title: backend/app/repositories/
description: Named persistence helpers that hide SQLAlchemy query details without owning business decisions.
resource: backend/app/repositories/
tags: [backend, flask, persistence]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Repository functions take a `Session` in and return an ORM row, scalar,
list, or tuple out:

- reads use `select()` and SQLAlchemy session helpers
- writes add, mutate, delete, and flush
- **commits stay in [services](/backend/services.md)**, never here

Keep a repository local to one persistence concern. If a function starts
coordinating multiple stores, permissions, or workflows, that behavior
belongs in a service instead.

# Citations

[1] [.claude/rules/repomap/backend-app-repositories.md](../../.claude/rules/repomap/backend-app-repositories.md)
