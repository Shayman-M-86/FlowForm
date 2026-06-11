# Session And Response Encryption Plan

This folder splits the original session and response encryption plan into focused documents.

## Start Here

- [Architecture](architecture.md) - purpose, goals, storage boundaries, and high-level system shape.
- [Project subjects](project-subjects.md) - project-scoped respondent identity relation and how sessions attach to it.
- [Project subject identity and access](subject-identity-and-access.md) - subject-resolution policy, identity attachments, recognition tokens, assigned links, and IP observations.
- [Core database schema](schema/core-database-schema.md) - core DB tables for sessions, subjects, links, and events.
- [Response database schema](schema/response-database-schema.md) - response DB tables for encrypted envelopes, logical answers, and revisions.
- [Cryptography](cryptography.md) - identifiers, secrets, locators, KMS envelope encryption, local answer encryption, and key caching.
- [Session flows](session-flows.md) - access resolution, session start/resume, question-view events, completion, abandonment, and expiry.
- [Answer flows](answer-flows.md) - answer saves, revision history, clearing answers, canonical answers, and idempotency.
- [Admin and operations](admin-and-operations.md) - admin reads, exports, deletion, consistency, IAM/KMS, rotation, logging, and failure scenarios.
- [Backend implementation](backend-implementation.md) - service boundaries, interfaces, API surface, schema notes, and local development.
- [API structure](api-structure.md) - authoritative respondent-facing API surface: endpoints, request/response shapes, status codes, and frontend call sequences.
- [Testing plan](testing-plan.md) - test coverage by behavior area.
- [Implementation order](implementation-order.md) - staged rollout, version-one decisions, and final summary.
- [Implementation checklist](implementation-checklist.md) - agent-ready task checklist for schema-first implementation.
- [Session service open issues](session-service-open-issues.md) - deferred policy items and defensive invariants found auditing the session services.
