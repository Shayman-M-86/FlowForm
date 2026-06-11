# Implementation Checklist

Agent-oriented checklist for implementing the session and response encryption plan.

This checklist assumes the current submission flow may be broken during the work and that no historical data migration is required. Schema compatibility with the legacy `SurveySubmission`, `Submission`, and `SubmissionAnswer` models is not a goal for the initial implementation.

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
- [ ] Read [project-subjects.md](project-subjects.md).
- [ ] Read [subject-identity-and-access.md](subject-identity-and-access.md).
- [ ] Read [schema/core-database-schema.md](schema/core-database-schema.md).
- [ ] Read [schema/response-database-schema.md](schema/response-database-schema.md).
- [ ] Read [backend-implementation.md](backend-implementation.md).
- [ ] Read [testing-plan.md](testing-plan.md).
- [ ] Inspect the current backend submission path:
  - [ ] `backend/app/api/v1/public.py`
  - [ ] `backend/app/api/v1/projects/submissions.py`
  - [ ] `backend/app/services/submissions.py`
  - [ ] `backend/app/gateway/submission_gateway.py`
  - [ ] `backend/app/schema/orm/core/submission_session.py`
  - [ ] `backend/app/schema/orm/core/project_subject.py`
  - [ ] `backend/app/schema/orm/response/response_envelope.py`
  - [ ] `backend/app/schema/orm/response/response_answer.py`
  - [ ] `backend/app/schema/orm/response/response_answer_revision.py`
  - [ ] `backend/app/schema/orm/response/submission_answer.py`

Done when:

- [ ] The agent can state which current files will be replaced, removed, or temporarily broken.
- [ ] The agent can state which public and admin routes will become the new source of truth.

## Phase 1: Schema First

- [x] Add or replace core ORM models for:
  - [x] `project_subjects`
  - [ ] `project_subject_identities`
  - [ ] `project_subject_tokens`
  - [x] `submission_sessions`
  - [x] `submission_events`
- [x] Add or replace response ORM models for:
  - [x] `response_envelopes`
  - [x] `response_answers`
  - [x] `response_answer_revisions`
- [x] Use the final encrypted response columns from the start:
  - [x] `session_locator`
  - [x] `linkage_key_version`
  - [x] `wrapped_dek`
  - [x] `kms_key_arn`
  - [x] `crypto_version`
  - [x] `answer_locator`
  - [x] `latest_revision_id`
  - [x] `ciphertext`
  - [x] `nonce`
  - [x] `revision_number`
- [x] Add database constraints that protect core invariants:
  - [x] unique browser session token hash
  - [x] valid session status values
  - [x] completed sessions have `completed_at`
  - [x] response envelope has a unique 32-byte `session_locator`
  - [x] response answer is unique by `(envelope_id, answer_locator)`
  - [x] answer revision is unique by `(answer_id, revision_number)`
  - [x] nonce is unique by `(envelope_id, nonce)`
  - [x] latest revision belongs to the same logical answer
- [x] Add schema creation/update path for both databases.
- [x] Remove or isolate old plaintext answer schema assumptions where they conflict.
- [x] Update `app/db/error_handling/integrity_rules.py` to cover the new core
      models (`ProjectSubject`, `SubmissionSession`, `SubmissionEvent`) and
      the new response models (`ResponseEnvelope`, `ResponseAnswer`,
      `ResponseAnswerRevision`).
- [x] Normalize `CheckConstraint` naming across `app/schema/orm/core/` to
      match the `NAMING_CONVENTION` in `app/db/base.py` (short names for
      single-table CHECKs, full explicit names for multi-column
      UNIQUE/FOREIGN KEY constraints).

Done when:

- [x] Core and response schemas can be created from an empty database.
- [x] ORM metadata includes the new tables.
- [x] Database-level constraints reject obvious invalid rows.

Test status (2026-06-10): fixed a stale composite-PK bug in
`test_survey_content.py` (4 tests, unrelated to this rework). Remaining 72
failures are all in old plaintext-submission tests hitting new
`response_envelopes` NOT NULL constraints — expected casualties to be deleted
once Phase 3-4 services replace the old submission path, not fixed now.

## Phase 2: API Contracts

- [x] Add public session routes:
  - [x] `POST /public/submission-sessions`
  - [x] `GET /public/submission-sessions/current`
  - [x] `PUT /public/submission-sessions/current/answers/{question_node_id}`
  - [x] `POST /public/submission-sessions/current/events/question-viewed`
  - [x] `POST /public/submission-sessions/current/complete`
- [x] Add administrator response routes:
  - [x] `GET /projects/{project_id}/surveys/{survey_id}/responses`
  - [x] `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`
  - [x] `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history`
  - [x] `POST /projects/{project_id}/surveys/{survey_id}/responses/export`
  - [x] `DELETE /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`
- [x] Add request and response schemas for:
  - [x] start session
  - [x] current session
  - [x] save answer
  - [x] question-viewed event
  - [x] complete session
  - [x] list admin responses
  - [x] admin response detail
  - [x] admin response history
- [x] Keep plaintext answers out of response-database API shapes.
- [x] Decide whether old `/public/submissions/slug` and `/public/submissions/link` routes are removed, disabled, or left temporarily broken.

Done when:

- [x] Routes exist and validate request shapes.
- [x] Routes return stable placeholder responses where service behavior is not implemented yet.
- [x] OpenAPI generation still works if this repo uses generated API docs.

Phase 2 public-contract status (2026-06-11):

- Added the five public respondent session route stubs in
  `backend/app/api/v1/public.py`.
- Moved link resolution from `GET /public/links/resolve?token=...` to
  `POST /public/links/resolve` with the token in the JSON body, matching
  `api-structure.md`.
- Added `backend/app/schema/api/requests/submission_sessions.py` and
  `backend/app/schema/api/responses/submission_sessions.py` for the public
  session contracts.
- Kept the old one-shot `/public/submissions/slug` and
  `/public/submissions/link` routes temporarily in place, with decommission
  TODOs beside the endpoints.
- Kept route behavior skeletal: the session routes validate the final request
  shapes and return stable placeholder response bodies/cookies until Phase 3-5
  services wire real core/response database behavior.
- Added `backend/tests/unit/test_submission_session_contracts.py` to pin the
  request validation and OpenAPI path/method contract.

Phase 2 admin-contract status (2026-06-11):

- Added the five administrator response route stubs in
  `backend/app/api/v1/projects/responses.py`, registered on `projects_bp`:
  list, detail, history, export, and delete. Each requires
  `@auth.require_auth()` and `submission:view` via `require_survey_permission`.
- Added `backend/app/schema/api/requests/responses.py`
  (`ListResponsesRequest`, `ExportResponsesRequest`) and
  `backend/app/schema/api/responses/responses.py` (response summary,
  paginated list, detail, history, and export shapes). Admin detail/history
  carry decrypted canonical answers keyed by `question_node_id` only — no
  response-database locators, crypto material, or `user_id` leak into the API.
- Kept behavior skeletal: handlers validate request shapes and return stable
  placeholder bodies (`responses_temp.py`) — empty list/detail/history,
  202 + null `download_url` for export, 204 for delete — until the Phase 7
  admin-read service derives locators and decrypts real envelopes.
- Added admin-contract coverage to
  `backend/tests/unit/test_submission_session_contracts.py` pinning request
  validation and the OpenAPI path/method contract for the five routes.
- Added a per-file `ARG001` ignore for `responses.py` in `pyproject.toml`:
  handlers must declare every path param for Flask binding and survey-access
  checks but cannot consume them all until the Phase 7 service lands.

## Phase 2.5: Subject Access Amendment

This amendment folds the project-subject access model into the Phase 2 contract
before Phase 3 service work begins. It keeps the public session contract stable
while making subject resolution explicit.

Already done:

- [x] Added [subject-identity-and-access.md](subject-identity-and-access.md) as
      the durable reference for subject resolution, identity attachments,
      recognition tokens, assigned links, IP observations, and service/API
      boundaries.
- [x] Linked the subject-access reference from [README.md](README.md) and Phase
      0 orientation.
- [x] Updated [architecture.md](architecture.md) so core owns
      `project_subjects`, `project_subject_identities`,
      `project_subject_tokens`, `survey_links.assigned_subject_id`,
      `submission_sessions`, and `subject_ip_observations`, while the response
      database receives none of those identifiers or identifying values.
- [x] Updated [schema/core-database-schema.md](schema/core-database-schema.md)
      and `infra/postgres/init/schema/flowform_core_db_schema_v4.sql` for:
  - [x] `project_subject_identities`
  - [x] `project_subject_tokens`
  - [x] `survey_links.assigned_subject_id`
  - [x] `subject_ip_observations`
  - [x] same-project foreign keys around subjects, links, sessions, response
        stores, and IP observations.
- [x] Added ORM/export coverage for `ProjectSubjectIdentity`,
      `ProjectSubjectToken`, and `SubjectIpObservation`.
- [x] Updated [session-flows.md](session-flows.md) so subject resolution occurs
      before core session creation, with explicit precedence rules for assigned
      subjects, authenticated context, verified email requirements, and
      subject-recognition cookies.
- [x] Updated [api-structure.md](api-structure.md) so subject recognition is
      server-side and distinct from survey-link tokens and submission resume
      tokens.
- [x] Updated [backend-implementation.md](backend-implementation.md) with the
      subject repositories, subject services, and orchestration boundary between
      `SurveyAccessResolver`, `ProjectSubjectResolver`, and `SessionStarter`.
- [x] Updated [testing-plan.md](testing-plan.md) with subject-access coverage
      for anonymous subject policy, recognition tokens, assigned links,
      identity conflicts/revocation, cross-project rejection, and IP-observation
      rules.

Still missing before/inside Phase 3:

- [ ] Finish the subject repositories and services described in
      [backend-implementation.md](backend-implementation.md); `POST
      /submission-sessions` now uses `SessionStarter`, while current-session,
      answer, event, and completion routes still use Phase 2/3 stubs.
- [x] Wire `ProjectSubjectResolver` into session start so
      `submission_sessions.project_subject_id` is resolved from server-owned
      access/auth/cookie context, never from browser-supplied IDs.
- [ ] Implement recognition-token issuance, rotation, expiry, revocation, and
      cookie naming/SameSite policy.
- [ ] Define the product policy for when anonymous access should create a
      `project_subjects` row versus leaving `project_subject_id` null.
- [ ] Define retention and access policy for `subject_ip_observations`.
- [ ] Keep explicit subject/email/auth identity-upgrade endpoints out of v1
      unless the product adds a respondent identity-upgrade UI.
- [ ] Delete `subject-access-doc-integration-checklist.md` once this amendment
      is fully integrated and the checklist is no longer useful.

## Phase 3: Service Skeleton Without Real Crypto

- [ ] Define final service/repository boundaries:
  - [x] core session repository
  - [ ] core event repository
  - [ ] response envelope repository
  - [ ] response answer repository
  - [ ] response revision repository
  - [x] session start service
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
  - [x] resolve access
  - [x] resolve the optional `project_subjects` row from server-owned link,
        auth, or recognition-token context
  - [ ] create anonymous `project_subjects` rows once product policy is set
  - [x] resolve authenticated-user identities through `project_subject_identities`
  - [x] resolve subject-recognition tokens through `project_subject_tokens`
  - [x] store `project_subjects.id` in `submission_sessions.project_subject_id`
        when the respondent is known
  - [x] leave `submission_sessions.project_subject_id` null for fully anonymous
        sessions
  - [x] bind one survey version
  - [x] generate a high-entropy browser token
  - [x] store only the token hash in core
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
