# Survey Branch-Key Encryption Refactor Plan

## Summary

Change FlowForm response encryption from direct per-session KMS wrapping to a survey branch-key hierarchy:

`AWS KMS -> survey branch key -> session DEK -> answer revisions`

This is a clean v4 contract change: no migrations, no backwards-compatible decrypt path, and no preservation of old `response_envelopes.wrapped_dek` rows. Survey encryption keys are created lazily at **survey publish time**. If a key already exists for the survey, republish reuses it unchanged. If KMS/encryption settings are unavailable during publish, publishing fails.

## Key Changes

- Add Core DB table/model `survey_encryption_keys` with one row per survey:
  `id`, `project_id`, `survey_id`, `wrapped_survey_branch_key`, `kms_key_arn`, `kms_context_version`, `created_at`, unique survey constraints, and same-project FK to `surveys(project_id, id)`.
- Change Response DB `response_envelopes`:
  rename `wrapped_dek` to `wrapped_session_dek`, remove `kms_key_arn` and `kms_context_version`, keep `crypto_version`.
- Keep Response DB anonymous:
  no `project_id`, `survey_id`, key version, or Core FK in Response DB.
- Add a survey branch-key repository/service:
  `ensure_for_survey(db, project_id, survey_id)` loads existing key or generates a 32-byte branch key, wraps it with KMS, stores it in Core, and returns the row.
- Add optional constructor injection to `SurveyService` so publish tests can provide a fake branch-key service.
- On `SurveyService.publish_version`, after publish prerequisites/default response-store setup and before final commit, call `ensure_for_survey`; the publish transaction rolls back if key creation fails.

## Crypto Design

- KMS only wraps/unwraps survey branch keys.
- Generate survey branch keys and session DEKs locally with `os.urandom(32)`.
- Cache plaintext survey branch keys for **1 hour** in worker memory, keyed by survey key row identity and KMS metadata.
- Keep the existing plaintext session DEK cache behavior, but update it to cache locally unwrapped session DEKs instead of KMS-unwrapped DEKs.
- Add local AES-256-GCM session-DEK wrapping:
  `wrapped_session_dek = nonce(12 bytes) || ciphertext_and_tag`.
- Add deterministic AAD helpers:
  - KMS encryption context for survey branch key: `purpose=survey_branch_key`, `project_id`, `survey_id`, `kms_context_version`.
  - Local session-DEK wrap AAD: `crypto_version`, `project_id`, `survey_id`, `session_id`, `session_locator`.
- Session start flow:
  load existing survey encryption key from Core, unwrap/cache survey branch key, generate session DEK, wrap it locally, store `wrapped_session_dek` in Response.
- Answer save/admin decrypt flow:
  load Core session, load survey encryption key, unwrap/cache survey branch key, use it to unwrap/cache session DEK, then encrypt/decrypt answer revisions with the session DEK.
- Current admin single-session decrypt paths use the same helper; future batch decrypt should group sessions by survey and unwrap each survey branch key once.

## Public Interfaces And Types

- No frontend/public API response shape changes.
- Backend ORM/API-internal changes:
  - add `SurveyEncryptionKey` Core ORM model and exports.
  - update `ResponseEnvelope.wrapped_dek` references to `wrapped_session_dek`.
  - update `CryptoServices` to include `survey_branch_key_service`.
  - replace direct per-session KMS semantics in `SessionDEKService` with local session-DEK wrap/unwrap using a provided plaintext survey branch key.
- Error behavior:
  - publish fails if survey key creation cannot reach KMS or encryption settings are missing.
  - session start fails if a published survey somehow has no `survey_encryption_keys` row.

## Test Plan

- Schema/ORM:
  run model metadata tests and add assertions for `SurveyEncryptionKey` uniques/FK plus updated `ResponseEnvelope` fields.
- Crypto unit tests:
  verify branch-key KMS context, 1-hour branch-key cache hit/miss, local session-DEK wrap/unwrap, AAD mismatch failure, and session DEK cache preservation.
- Publish tests:
  first publish creates exactly one survey key; republish reuses the existing row; KMS/key-service failure prevents publish.
- Session start tests:
  response envelope stores `wrapped_session_dek`; no KMS metadata appears in Response DB; KMS is called only for survey branch-key unwrap on cache miss.
- Answer/admin decrypt tests:
  answer save decrypts survey branch key once per cache TTL, unwraps session DEK locally, and continues to encrypt/decrypt answer revisions correctly.
- Regression tests:
  update existing response repo, session start, answer save, completion, deletion, admin decrypt, and e2e fixtures that currently assert or seed `wrapped_dek`, `kms_key_arn`, or `kms_context_version`.

## Assumptions

- No migration/backfill is required; existing encrypted data can be discarded or recreated.
- One stable survey branch key per survey; no survey key version is added.
- Existing survey key rows are never replaced on republish, even if current KMS config changes.
- `crypto_version=1` covers both local session-DEK wrapping format and answer-revision encryption format.
- The implementation should also create a durable repo plan doc at `docs/session-encryption/survey-branch-key-implementation-plan.md` when execution mode is available.
