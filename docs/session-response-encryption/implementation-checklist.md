# Implementation Checklist

Agent-oriented checklist for implementing the session and response encryption plan.

This checklist assumes the current submission flow may be broken during the work and that no historical data migration is required. Schema compatibility with the existing `SurveySubmission`, `Submission`, and `SubmissionAnswer` model is not a goal for the initial implementation.

## Ground Rules

- [ ] Treat this as a replacement session/response system, not a patch over plaintext `answer_value`.
- [ ] Keep the final encrypted response table shape from the first schema pass, even while crypto behavior is stubbed.
- [ ] Keep core and response database responsibilities separate.
- [ ] Keep cross-database orchestration in services, not repositories.
- [ ] Repositories should normally touch only one database.
- [ ] Do not return a browser resume token until the required core and response records both exist.
- [ ] Do not claim answer-save success until the response-side answer revision has committed.
- [ ] Treat analytics events as secondary metadata; they must not make a failed answer write look successful.

## Phase 0: Repo Orientation

- [ ] Read [README.md](README.md).
- [ ] Read [architecture.md](architecture.md).
- [ ] Read [schema/core-database-schema.md](schema/core-database-schema.md).
- [ ] Read [schema/response-database-schema.md](schema/response-database-schema.md).
- [ ] Read [backend-implementation.md](backend-implementation.md).
- [ ] Read [testing-plan.md](testing-plan.md).
- [ ] Inspect the current backend submission path:
  - [ ] `backend/app/api/v1/public.py`
  - [ ] `backend/app/api/v1/projects/submissions.py`
  - [ ] `backend/app/services/submissions.py`
  - [ ] `backend/app/gateway/submission_gateway.py`
  - [ ] `backend/app/schema/orm/core/survey_submission.py`
  - [ ] `backend/app/schema/orm/response/submission.py`
  - [ ] `backend/app/schema/orm/response/submission_answer.py`

Done when:

- [ ] The agent can state which current files will be replaced, removed, or temporarily broken.
- [ ] The agent can state which public and admin routes will become the new source of truth.

## Phase 1: Schema First

- [ ] Add or replace core ORM models for:
  - [ ] `project_subjects`
  - [ ] `submission_sessions`
  - [ ] `submission_events`
- [ ] Add or replace response ORM models for:
  - [ ] `response_envelopes`
  - [ ] `response_answers`
  - [ ] `response_answer_revisions`
- [ ] Use the final encrypted response columns from the start:
  - [ ] `session_locator`
  - [ ] `linkage_key_version`
  - [ ] `wrapped_dek`
  - [ ] `kms_key_arn`
  - [ ] `crypto_version`
  - [ ] `answer_locator`
  - [ ] `latest_revision_id`
  - [ ] `ciphertext`
  - [ ] `nonce`
  - [ ] `revision_number`
- [ ] Add database constraints that protect core invariants:
  - [ ] unique browser session token hash
  - [ ] valid session status values
  - [ ] completed sessions have `completed_at`
  - [ ] response envelope has a unique 32-byte `session_locator`
  - [ ] response answer is unique by `(envelope_id, answer_locator)`
  - [ ] answer revision is unique by `(answer_id, revision_number)`
  - [ ] nonce is unique by `(envelope_id, nonce)`
  - [ ] latest revision belongs to the same logical answer
- [ ] Add schema creation/update path for both databases.
- [ ] Remove or isolate old plaintext answer schema assumptions where they conflict.

Done when:

- [ ] Core and response schemas can be created from an empty database.
- [ ] ORM metadata includes the new tables.
- [ ] Database-level constraints reject obvious invalid rows.

## Phase 2: API Contracts

- [ ] Add public session routes:
  - [ ] `POST /public/submission-sessions`
  - [ ] `GET /public/submission-sessions/current`
  - [ ] `PUT /public/submission-sessions/current/answers/{question_node_id}`
  - [ ] `POST /public/submission-sessions/current/events/question-viewed`
  - [ ] `POST /public/submission-sessions/current/complete`
- [ ] Add administrator response routes:
  - [ ] `GET /projects/{project_id}/surveys/{survey_id}/responses`
  - [ ] `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`
  - [ ] `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history`
  - [ ] `POST /projects/{project_id}/surveys/{survey_id}/responses/export`
  - [ ] `DELETE /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`
- [ ] Add request and response schemas for:
  - [ ] start session
  - [ ] current session
  - [ ] save answer
  - [ ] question-viewed event
  - [ ] complete session
  - [ ] list admin responses
  - [ ] admin response detail
  - [ ] admin response history
- [ ] Keep plaintext answers out of response-database API shapes.
- [ ] Decide whether old `/public/submissions/slug` and `/public/submissions/link` routes are removed, disabled, or left temporarily broken.

Done when:

- [ ] Routes exist and validate request shapes.
- [ ] Routes return stable placeholder responses where service behavior is not implemented yet.
- [ ] OpenAPI generation still works if this repo uses generated API docs.

## Phase 3: Service Skeleton Without Real Crypto

- [ ] Define final service/repository boundaries:
  - [ ] core session repository
  - [ ] core event repository
  - [ ] response envelope repository
  - [ ] response answer repository
  - [ ] response revision repository
  - [ ] session start service
  - [ ] session resume service
  - [ ] answer save service
  - [ ] completion service
  - [ ] admin response read service
- [ ] Add temporary crypto interfaces with dev implementations:
  - [ ] linkage secret provider
  - [ ] locator service
  - [ ] DEK provider
  - [ ] answer cipher
  - [ ] AAD builder
- [ ] The dev implementations may use deterministic fake locators and reversible placeholder ciphertext.
- [ ] The dev implementations must preserve final method signatures and data shapes.
- [ ] Session start should:
  - [ ] resolve access
  - [ ] bind one survey version
  - [ ] generate a high-entropy browser token
  - [ ] store only the token hash in core
  - [ ] create a response envelope
  - [ ] return the raw browser token only after both stores succeed
- [ ] Session resume should:
  - [ ] hash the browser token
  - [ ] load an in-progress session
  - [ ] reject expired, completed, or abandoned sessions
  - [ ] return current canonical answers when available

Done when:

- [ ] Public session start/resume works against empty databases.
- [ ] A response envelope is provisioned for every started session.
- [ ] The code uses final crypto interfaces, even though real cryptography is not active yet.

## Phase 4: Answer Revision Mechanics

- [ ] Implement answer validation against the frozen survey version.
- [ ] Implement first answer save:
  - [ ] derive or fake `answer_locator`
  - [ ] create `response_answers`
  - [ ] create revision one
  - [ ] set `latest_revision_id`
  - [ ] record `answer_saved` event after the response write commits
- [ ] Implement changed answer save:
  - [ ] find logical answer by `(envelope_id, answer_locator)`
  - [ ] insert the next immutable revision
  - [ ] update `latest_revision_id`
- [ ] Implement clear-answer save as a revision, not a deletion.
- [ ] Implement `client_mutation_id` idempotency if it is part of the route contract.
- [ ] Add concurrency handling for simultaneous first saves and simultaneous updates.

Done when:

- [ ] Latest revision is the canonical answer.
- [ ] Historical revisions remain readable by admin-only service code.
- [ ] Retrying the same mutation does not create duplicate revisions.
- [ ] The database rejects nonce reuse within one envelope.

## Phase 5: Completion And Session Lifecycle

- [ ] Implement question-viewed events.
- [ ] Implement completion:
  - [ ] validate required canonical answers
  - [ ] set session status to `completed`
  - [ ] set `completed_at`
  - [ ] reject further respondent edits
- [ ] Implement abandonment/expiry behavior:
  - [ ] reject expired session writes
  - [ ] provide a maintenance path for stale in-progress sessions
  - [ ] preserve or delete partial responses according to product rules

Done when:

- [ ] Completion freezes the session.
- [ ] Repeated completion requests are safe.
- [ ] Answer save and completion cannot race into an inconsistent state.

## Phase 6: Real Cryptography

- [ ] Replace dev linkage provider with Secrets Manager-backed linkage secret loading.
- [ ] Add linkage secret cache.
- [ ] Implement HMAC-SHA-256 session locators.
- [ ] Implement HMAC-SHA-256 answer locators.
- [ ] Replace dev DEK provider with KMS `GenerateDataKey`.
- [ ] Store wrapped DEK on `response_envelopes`.
- [ ] Add DEK decrypt path for reads.
- [ ] Add short-lived DEK cache.
- [ ] Implement stable AAD construction.
- [ ] Implement AES-256-GCM answer encryption/decryption.
- [ ] Generate a fresh 12-byte nonce for every answer revision.
- [ ] Ensure plaintext DEKs and plaintext answers are not logged or persisted.

Done when:

- [ ] Encrypted answer save and decrypt read round-trip correctly.
- [ ] Tampered ciphertext, nonce, AAD, or DEK fails closed.
- [ ] Old linkage-key versions remain usable for existing sessions.
- [ ] New sessions use the active linkage-key version.

## Phase 7: Admin Reads, Export, And Deletion

- [ ] Implement admin list responses from core session metadata.
- [ ] Implement admin detail read:
  - [ ] authorize project/survey access
  - [ ] derive session locator
  - [ ] load response envelope
  - [ ] decrypt canonical answer revisions
  - [ ] validate decrypted question IDs against locators
- [ ] Implement optional revision-history read.
- [ ] Implement export using the same authorization and decrypt path as detail read.
- [ ] Implement delete:
  - [ ] remove or tombstone core session metadata according to product rules
  - [ ] remove response envelope and cascading response rows
  - [ ] handle pending deletion if one database succeeds and the other fails
- [ ] Add privileged-access audit logs without plaintext answers.

Done when:

- [ ] Admin reads never bypass the decrypt/authorization service path.
- [ ] Exports use the same response shaping rules as admin reads.
- [ ] Deletion can be retried safely.

## Phase 8: Frontend Integration

- [ ] Update Public Site to start or resume a submission session before saving answers.
- [ ] Save answers incrementally through the session answer route.
- [ ] Complete the session through the completion route.
- [ ] Handle expired, completed, abandoned, and invalid session responses.
- [ ] Update Studio results views to use the new admin response routes.
- [ ] Remove frontend assumptions that a submission is created only once at final submit.

Done when:

- [ ] A respondent can start, resume, save answers, complete, and refresh without losing committed answers.
- [ ] Studio can list and inspect completed responses through the new API.

## Phase 9: Verification And Hardening

- [ ] Implement the tests in [testing-plan.md](testing-plan.md).
- [ ] Add cross-database failure tests:
  - [ ] core write succeeds and response envelope fails
  - [ ] response answer succeeds and analytics event fails
  - [ ] KMS fails
  - [ ] Secrets Manager fails on cache miss
  - [ ] response database is unavailable
- [ ] Add reconciliation task:
  - [ ] core sessions without response envelopes
  - [ ] stale session-initialization failures
  - [ ] pending deletions
  - [ ] inconsistent linkage-key versions
  - [ ] missing response envelopes during admin reads
- [ ] Add metrics for session starts, answer saves, completions, decrypt failures, KMS failures, and reconciliation repairs.
- [ ] Sanitize logs and Sentry payloads.
- [ ] Add IAM/KMS policy documentation.
- [ ] Add key-rotation runbook.

Done when:

- [ ] The encrypted session flow passes unit and integration tests.
- [ ] Failure paths return safe errors.
- [ ] Logs contain no plaintext answers, browser tokens, plaintext DEKs, or raw linkage secrets.
- [ ] Operational docs describe how to rotate keys and reconcile partial failures.

## Suggested First Pull Request

- [ ] Add the new ORM models and schema creation path.
- [ ] Add minimal tests proving the empty schemas can be created.
- [ ] Add constraint tests for the response schema invariants.
- [ ] Do not implement public routes in the same PR unless the schema diff is small.

The first PR is done when an empty local database can create the final core and response tables and reject invalid rows for the most important invariants.
