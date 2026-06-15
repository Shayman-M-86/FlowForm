# Session And Response Encryption

This folder is the consolidated reference for FlowForm's session/response
encryption work. It separates current implementation truth from the remaining
roadmap so future agents do not need to reconcile older phase notes, dated
summaries, and schema drafts by hand.

## Current State

Phase 1 schema work is in place. The subject-access model and session-start
path are mostly real: link resolution, authenticated-link participant checks,
subject resolution, and `POST /api/v1/public/submission-session/start` all run
through live services and integration tests. Resume, answer save,
question-viewed events, completion, response-envelope creation, admin reads,
frontend incremental saves, and real cryptography are still pending or
placeholder-only.

## Docs

- [Architecture](architecture.md) - conceptual boundaries: core vs. response
  storage, identity separation, locators, frontend/backend responsibilities,
  and implementation status.
- [Data model](data-model.md) - current core and response schema, including
  `project_subjects`, `project_participants`, `submission_sessions`,
  `response_envelopes`, answers, revisions, and key constraints.
- [Flows](flows.md) - respondent-facing flows as currently implemented,
  including link resolution, subject resolution, session start, and the
  stubbed resume/save/event/complete paths.
- [API surface](api-surface.md) - current REST routes, with each route marked
  real, placeholder, removed, or planned.
- [Cryptography plan](cryptography-plan.md) - forward-looking design for
  HMAC locators, KMS-backed DEKs, AES-GCM answer encryption, AAD, caching,
  and rotation. This is not implemented yet.
- [Remaining work](remaining-work.md) - actionable roadmap by phase, plus
  open product/engineering decisions.
- [Testing plan](testing-plan.md) - coverage already present and tests that
  become possible after later phases land.

The SQL files remain the source of truth for raw schema details:

- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`
