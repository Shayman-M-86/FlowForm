---
paths: backend/app/**
---

# backend/app/

_Last updated: 2026-05-27 by /repomap_

The top-level Flask application package. It exposes a single `create_app` factory (in `app/core/factory.py`) that wires together extensions, dual-database sessions (core + response), the v1 API blueprint, rate limiting, error handlers, and seed data. Subdirectories follow a strict layered architecture: `api`, `core`, `db`, `domain`, `gateway`, `logging`, `middleware`, `openapi`, `repositories`, `schema`, `services`, and `utils`.
