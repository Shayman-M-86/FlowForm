# Backend modernization

**Status: Proposal — 2026-11-22.**

## Context

The Python backend is being reconsidered for simpler component ownership and lower per-request overhead.

## Proposed direction

Adopt Litestar for HTTP execution and use a feature-based modular monolith. Feature services remain close to API workflows. Capabilities supply reusable functionality across features and workers. Repositories provide explicit data access and accept a workflow-owned session context.

## Open decisions

Migration sequence, query layer choices, compatibility strategy, performance validation and release plan remain to be specified. The current Flask implementation must not be described as migrated.
