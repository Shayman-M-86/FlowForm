# Response Encryption Service

This document describes the target service FlowForm still needs to build for
encrypted session responses. It is deliberately not an access-control document.
By the time this service runs, the caller has already resolved the public link,
subject, session, survey version, and authorization question.

The service turns a core submission session into anonymous encrypted response
records.

## Service Contract

The service should expose backend-internal operations shaped around the
submission lifecycle:

- create an envelope for a new `submission_sessions.id`;
- save one answer revision for a session and question;
- load canonical answers for an authorized backend workflow;
- complete response-side checks needed by session completion;
- delete response-side material for a session.

These operations should be called from application services that already own
route orchestration and core-database writes. Cross-database coordination stays
in `services/`; response models should not reach back into core tables.

## Inputs

The service may receive:

- `submission_session_id` from the core database;
- frozen survey/version metadata needed for validation context;
- `question_node_id` or the stable published question identifier;
- canonical answer payload JSON;
- `client_mutation_id` for idempotent answer saves;
- backend actor/context for audit decisions that already passed
  authorization.

The service should not receive email addresses, user IDs, recognition tokens,
participant IDs, or project-subject identity details unless a narrow audit log
explicitly requires them on the core side. None of those values belong in the
response database.

## Stored Response Data

The response database should store only anonymous encrypted response material:

- `response_envelopes.session_locator`;
- `response_envelopes.wrapped_dek`;
- KMS and crypto version metadata;
- `response_answers.answer_locator`;
- immutable `response_answer_revisions` rows;
- ciphertext, nonce, revision number, and `client_mutation_id`.

The response database must not store the core session UUID, project ID, survey
ID, user ID, subject ID, participant ID, link token, recognition token, email,
IP address, plaintext question ID, or plaintext answer.

## Locator Model

The service derives response-side locators from core-side identifiers using
versioned HMAC inputs described in the cryptography plan.

- `session_locator` identifies the response envelope for one core submission
  session.
- `answer_locator` identifies one logical question answer within that envelope.

These locators are deterministic for the backend and opaque to the database.
They let the backend find response records without storing direct core foreign
keys in the response database.

## Envelope Creation

When a core submission session is created, the target service should create the
matching response envelope.

The envelope creation flow is:

1. Derive `session_locator` from `submission_sessions.id`.
2. Generate a per-session DEK through the configured KMS path.
3. Store only the wrapped DEK and crypto metadata in `response_envelopes`.
4. Discard the plaintext DEK after immediate use, or keep it only in a short,
   bounded in-memory cache.

Envelope creation should be idempotent for the core session. Retrying a start
workflow must not create multiple envelopes for the same session locator.

## Answer Save

Answer saving should append encrypted revisions, not overwrite encrypted
payloads in place.

The target save flow is:

1. The caller verifies the session can still accept edits.
2. The caller validates and canonicalizes the answer against the frozen survey
   version.
3. The response-encryption service derives `session_locator` and
   `answer_locator`.
4. The service loads the envelope and unwraps the session DEK.
5. The service encrypts the canonical answer payload with AES-GCM and stable
   AAD.
6. The service inserts a new `response_answer_revisions` row.
7. The service advances `response_answers.latest_revision_id`.
8. The caller records the core-side `answer_saved` event.

`client_mutation_id` should make retries safe. A duplicate mutation for the
same answer should return the already-recorded result instead of creating a
second logical write.

## Reads And Decryption

Decryption is a backend-only capability. It is used after a caller has already
passed core-side authorization.

Expected callers include:

- Studio response detail views;
- exports;
- deletion or retention workflows that need to locate response material;
- internal completion checks that need canonical answer state.

The public respondent API should not grow a general current-session read route
for arbitrary in-progress encrypted answers. If a future product flow needs a
resume experience, it should define a narrow route contract first, then call
this service as an implementation detail.

## Completion

Completion remains a core lifecycle decision. The response-encryption service
can help load canonical answer state, but it should not decide whether a user
was allowed to submit the survey.

The completion flow should:

1. reject edits after the core session is completed;
2. validate required canonical answers against the frozen survey version;
3. record response-side state only as needed;
4. mark the core session completed and write the core event in the same
   orchestration layer that coordinates both databases.

## Failure Rules

The service should fail closed.

- If the envelope cannot be created, the session-start workflow should not
  report a fully usable encrypted session.
- If KMS cannot unwrap the DEK, answer reads and writes should fail.
- If encryption succeeds but the revision write fails, the caller should retry
  using `client_mutation_id`.
- If a core event write fails after response persistence, recovery should be
  explicit and idempotent; do not silently create a second encrypted revision.

## Implementation Status

The schema columns already exist for the target model, but the service
described here is not implemented yet. Current code still needs the envelope
creation path, answer-revision persistence, KMS/DEK handling, AES-GCM
encryption, decrypt reads, delete support, and lifecycle coordination.
