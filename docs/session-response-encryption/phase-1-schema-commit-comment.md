# Phase 1 Schema Commit Comment

Generated from the unstaged working-tree diff on 2026-06-10.

## Proposed Commit Subject

```text
schema: stage encrypted submission session response tables
```

## Proposed Commit Body

This commit moves the submission model into the Phase 1 shape from the session
and response encryption plan. The old plaintext submission-row model is no
longer the target: core owns respondent/session metadata and analytics events;
the response database owns pseudonymous encrypted storage through envelopes,
logical answers, and immutable answer revisions.

The final encrypted table shape lands before the service and real crypto layers,
giving later phases stable invariants: a core session must exist; the response
side must have a pseudonymous envelope; each logical answer is found through an
answer locator; and each answer mutation becomes an encrypted revision with
idempotency and nonce constraints.

Phase 1 is checked off. API contracts, service orchestration, answer-save
mechanics, lifecycle routes, real cryptography, admin reads, frontend
integration, and hardening remain later-phase work.

## What Changed

### Core database model

- Replaces the old core submission identity shape with `project_subjects`,
  `submission_sessions`, and `submission_events`.
- Keeps respondent identity, survey/session ownership, access-link references,
  browser resume token hashes, lifecycle status, and event metadata in core.
- Adds constraints for unique browser session token hashes, valid session
  statuses, completed-session timestamps, same-project/same-survey foreign
  keys, and event payload bounds.
- Changes survey question node ids from integers to UUIDs so events and future
  answer flows can refer to stable globally unique nodes.
- Adds `(survey_version_id, id)` uniqueness for survey questions so
  session/event rows can enforce that referenced questions belong to the same
  survey version.
- Normalizes single-table `CheckConstraint` names to the repo convention while
  keeping multi-column unique and foreign-key names explicit and descriptive.

### Response database model

- Replaces the plaintext response-side submission/answer/event shape with
  `response_envelopes`, `response_answers`, and `response_answer_revisions`.
- Uses a 32-byte `session_locator` for anonymous linkage instead of a core
  submission id or user-facing identifier.
- Adds the final encrypted-response columns from the start:
  `linkage_key_version`, `wrapped_dek`, `kms_key_arn`, `crypto_version`,
  `answer_locator`, `latest_revision_id`, `ciphertext`, `nonce`, and
  `revision_number`.
- Uses `response_answers` as the stable logical-answer row and
  `response_answer_revisions` as append-only encrypted mutation history.
- Adds constraints for unique `session_locator`; valid locator and encrypted
  blob lengths; unique `(envelope_id, answer_locator)`; unique
  `(answer_id, revision_number)`; unique `(envelope_id, nonce)`; idempotent
  `(answer_id, client_mutation_id)`; and a deferrable same-answer
  latest-revision relationship.

### ORM exports and temporary compatibility aliases

- Updates `backend/app/schema/orm/__init__.py`,
  `backend/app/schema/orm/core/__init__.py`, and
  `backend/app/schema/orm/response/__init__.py` so metadata includes the new
  models.
- Converts legacy import modules into temporary aliases:
  `ResponseSubjectMapping -> ProjectSubject`,
  `SurveySubmission -> SubmissionSession`,
  `Submission -> ResponseEnvelope`,
  `SubmissionAnswer -> ResponseAnswer`, and
  response-side `SubmissionEvent -> core SubmissionEvent`.
- These aliases are deliberate short-term scaffolding, not the final API. They
  prevent import explosions while Phase 2 through Phase 4 move routes,
  factories, and services to the new names.

### Integrity error translation

- Updates `backend/app/db/error_handling/integrity_rules.py` for the new core and
  response ORM contexts.
- Replaces the old `SurveySubmission` and `ResponseSubjectMapping` focus with
  coverage for `ProjectSubject`, `SubmissionSession`, `SubmissionEvent`,
  `ResponseEnvelope`, `ResponseAnswer`, and `ResponseAnswerRevision`.
- Adds error-context parameters for session ids/status, event ids/types,
  project subject ids, question node ids, envelope ids, answer ids, revision
  ids, locator fields, nonce/ciphertext fields, and client mutation ids.
- This matters because Phase 1 is constraint-heavy: bad states should be
  rejected early and translated into useful application-level errors.
- **Known regression:** mappings for `ck_survey_roles_description_len` and
  `ck_project_roles_description_len` were also dropped. These unrelated
  constraints still exist unchanged in `survey_access.py`/`project.py`, but now
  fall through to an unmapped error instead of `ROLE_DESCRIPTION_INVALID`.
  Restore the mappings before this commit, or in a follow-up before merge.

### SQL schema and seed data

- Updates `infra/postgres/init/schema/flowform_core_db_schema_v4.sql` and
  `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`.
- Updates core and response mock data for the Phase 1 layout.
- Removes or isolates old plaintext answer assumptions where they conflict with
  the encrypted shape.
- Keeps SQL creation aligned with ORM definitions so an empty local database can
  be created with the new tables and constraints.

### Documentation and checklist

- Marks Phase 1 complete and names the actual new model files instead of legacy
  submission files.
- Adds checklist items for integrity-rule coverage and core `CheckConstraint`
  naming normalization.
- Updates core and response schema docs for the new Phase 1 table shapes.
- Removes stale response crypto column references from backend implementation
  notes.

## Checklist Comparison

The diff supports the checklist's Phase 1 completion claim:

- Core ORM models for `project_subjects`, `submission_sessions`, and
  `submission_events`: implemented and exported.
- Response ORM models for `response_envelopes`, `response_answers`, and
  `response_answer_revisions`: implemented and exported.
- Final encrypted response columns: present in the response ORM/schema shape.
- Core and response constraints: added for session status, completion,
  locators, answer uniqueness, revision order, nonce uniqueness, and
  same-answer latest-revision integrity.
- Schema creation/update path: reflected in the SQL init files.
- Old plaintext assumptions: isolated behind temporary compatibility imports
  and called out as expected casualties.
- Integrity error rules: updated for the new model set.
- Constraint naming: normalized across touched core ORM files.

Later phases remain open:

- Phase 2 API routes.
- Phase 3 service/repository orchestration.
- Phase 4 answer revision write mechanics.
- Phase 5 lifecycle behavior.
- Phase 6 real KMS/local crypto.
- Phase 7 admin reads/export/deletion.
- Phase 8 frontend integration.
- Phase 9 hardening.

## Why This Is Being Done Now

This foundation commit chooses schema truth before behavior. The difficult part
is not only encrypting a JSON value; it is separating identity-bearing session
metadata from anonymous response payload storage and enforcing that split in
the database.

The old path centered on plaintext submission and answer rows. The new contract
is:

- core knows who, what survey, what session, what lifecycle state, and what
  event happened;
- response knows only an anonymous envelope, answer locators, encrypted blobs,
  nonces, and revisions;
- services will later coordinate both databases and refuse to report success
  until required core and response writes have both committed.

Landing the schema first lets Phase 2 build APIs and service skeletons against
the destination shape instead of adapters around tables that are about to
disappear.

## Current Risk and Expected Breakage

- The current submission flow may remain broken during the rework.
- Legacy tests and factories creating `SurveySubmission`, `Submission`,
  `SubmissionAnswer`, or `ResponseSubjectMapping` rows will fail until deleted
  or rewritten for the session/envelope/answer model.
- Temporary aliases are intentionally short-lived and should not become a
  permanent compatibility layer.
- The response tables have crypto-shaped columns, but this diff does not
  implement real cryptography or KMS behavior.
- The new constraints are stricter than the plaintext shape, so future service
  work must create records in the correct order.

## Validation Notes

Test run performed during this session (2026-06-10), recorded in the checklist:

- A stale composite-primary-key expectation in
  `backend/tests/integration/core/test_survey_content.py` was fixed for four
  tests, which passed after the fix.
- The remaining 72 failures are expected in old plaintext-submission tests and
  factories because they still target the removed legacy shape and hit the new
  `response_envelopes` constraints.

This draft did not independently rerun the test suite; it relies on that test
run. The checklist asserts that schema creation succeeds from an empty
database, but this draft has not separately verified the raw SQL init files.

## Files Touched By The Current Diff

Backend ORM and integrity handling:

- `backend/app/db/error_handling/integrity_rules.py`
- `backend/app/schema/orm/__init__.py`
- `backend/app/schema/orm/core/__init__.py`
- `backend/app/schema/orm/core/invitation.py`
- `backend/app/schema/orm/core/project.py`
- `backend/app/schema/orm/core/response_subject_mapping.py`
- `backend/app/schema/orm/core/survey_access.py`
- `backend/app/schema/orm/core/survey_content.py`
- `backend/app/schema/orm/core/survey_submission.py`
- `backend/app/schema/orm/response/__init__.py`
- `backend/app/schema/orm/response/submission.py`
- `backend/app/schema/orm/response/submission_answer.py`
- `backend/app/schema/orm/response/submission_event.py`

New (untracked):

- `backend/app/schema/orm/core/project_subject.py`
- `backend/app/schema/orm/core/submission_session.py`
- `backend/app/schema/orm/response/response_envelope.py`
- `backend/app/schema/orm/response/response_answer.py`
- `backend/app/schema/orm/response/response_answer_revision.py`

Tests:

- `backend/tests/integration/core/test_survey_content.py`

Docs:

- `docs/session-response-encryption/backend-implementation.md`
- `docs/session-response-encryption/implementation-checklist.md`
- `docs/session-response-encryption/schema/core-database-schema.md`
- `docs/session-response-encryption/schema/response-database-schema.md`

Database bootstrap and mock data:

- `infra/postgres/flowform_core_mock_data.sql`
- `infra/postgres/flowform_response_mock_data.sql`
- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`

## Suggested Next Commit After This

Start Phase 2 by adding the public session API contract over the new schema:

- `POST /public/submission-sessions`
- `GET /public/submission-sessions/current`
- `PUT /public/submission-sessions/current/answers/{question_node_id}`
- `POST /public/submission-sessions/current/events/question-viewed`
- `POST /public/submission-sessions/current/complete`

Keep route behavior skeletal at first, but use the new session/envelope
vocabulary in request and response models so old plaintext submissions stop
leaking into the new API surface.
