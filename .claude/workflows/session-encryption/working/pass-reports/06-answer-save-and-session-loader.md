## Pass report

Pass: 06 — Answer Save and Session Loader

Changed files:
* `backend/app/services/public_submissions/core/session_loader.py` — new: shared current-session loader
* `backend/app/services/public_submissions/core/answer_save.py` — new: 12-step answer save + question-viewed event
* `backend/app/repositories/core/submission_sessions.py` — added `get_by_token_hash()`, `lock_for_update()`
* `backend/app/repositories/core/submission_events.py` — new: `create_event()` for analytics events
* `backend/app/repositories/response/response_answer_revision_repo.py` — added optional `revision_id` param to `create()`
* `backend/app/crypto/aad.py` — changed `build_aad` to accept `uuid.UUID` instead of `int` for envelope_id, answer_id, revision_id
* `backend/app/domain/errors.py` — added `SessionNotFoundError`, `SessionExpiredError`, `SessionInvalidError`, `EnvelopeNotFoundError`, `AnswerSaveError`, `QuestionNotInVersionError`
* `backend/tests/unit/services/test_session_loader.py` — new: 6 unit tests for state rejection
* `backend/tests/unit/crypto/test_aad.py` — updated to use UUID-based AAD inputs
* `backend/tests/integration/core/test_answer_save.py` — new: 6 integration tests for answer save + question viewed

Behavior implemented:
* Session loader reads browser resume token, hashes it, loads core session by hash, loads frozen survey version, rejects missing/expired/abandoned/completed states, derives session locator, loads response envelope, returns `SessionContext`
* `allow_completed=True` flag permits completed sessions (for completion/admin reads)
* 12-step answer save follows exact order from doc 03: lock session → mutation ID dedup → validate question → derive locators → load DEK (cache or KMS unwrap) → encrypt → insert revision → update latest pointer → commit response → insert analytics event → commit core
* Mutation ID dedup returns existing revision without creating duplicates
* Analytics event failure (steps 11-12) is logged and swallowed — response write is authoritative
* Question-viewed event validates question belongs to frozen version, writes core event, swallows failure
* First-save race handled via `get_or_create` unique constraint on `(envelope_id, answer_locator)`

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "answer_save or session_loader or test_aad"` — 17 passed
* `bash backend/scripts/run-tests.sh --ai -k "crypto"` — 39 passed
* `bash backend/scripts/run-tests.sh --ai -k "session_start or response_repo"` — 31 passed

Failures or skipped validation:
* none

Policy change during pass:
* `build_aad()` signature changed from `int` IDs to `uuid.UUID` IDs. All DB models use UUID primary keys (`server_default=func.gen_random_uuid()`), so the original integer-based AAD packing was incompatible. Updated to pack UUID bytes (16 bytes each) instead of 8-byte integers. AAD unit tests updated to match. This is a breaking change to the Pass 01 contract but the old signature was never used with real DB rows.

Trace notes:
* entry points touched: `session_loader.load_current_session()`, `AnswerSaveService.save_answer()`, `AnswerSaveService.record_question_viewed()`
* service methods touched: `_derive_answer_locator()`, `_get_or_unwrap_dek()`, `_validate_question_in_version()`
* repository helpers touched: `submission_sessions.get_by_token_hash()`, `submission_sessions.lock_for_update()`, `submission_events.create_event()`, `response_answer_revision_repo.create()` (added `revision_id` param)
* side effects changed: new core analytics events (`answer_saved`, `question_viewed`) written via `submission_events.create_event()`
* transaction boundary changed or unchanged: response DB committed at step 10 before core analytics; core committed at step 12 as secondary — matches doc 03/06 authoritative-write rule
* tests that now describe behavior: `TestSessionLoaderRejection` (6 tests), `TestAnswerSave` (4 tests), `TestQuestionViewed` (2 tests)

Remaining risks:
* Answer validation against frozen survey version (step 3) currently only checks that the question node ID exists in the version. Full answer-shape validation (required fields, value type checks) is not implemented — belongs to a later pass or a domain validation module.
* The `revision_id` is pre-generated (`uuid.uuid4()`) before insertion so it can be included in AAD. If the DB rejects the pre-generated UUID (collision), the save fails. Risk is negligible for UUIDv4.
* `build_aad` contract change: any code that called the old integer-based signature will break. Only the unit tests used it; no other callers existed.

## Pass-forward

* `session_loader.load_current_session(db, response_db, raw_resume_token, *, allow_completed, encryption_settings)` returns `SessionContext(session, survey_version, session_locator, envelope, encryption_settings)`. Use this for all integration tests that need a loaded session.
* `AnswerSaveService(dek_cache=...).save_answer(db, response_db, ctx=..., question_node_id=..., answer_state=..., answer_value=..., client_mutation_id=...)` returns the `revision_id` (UUID).
* `build_aad()` now accepts `uuid.UUID` for `envelope_id`, `answer_id`, `revision_id` — not `int`. Integration tests verifying decrypt round-trips must use UUID-based AAD.
* `response_answer_revision_repo.create()` accepts optional `revision_id` to pre-set the UUID before insertion (needed for AAD binding).
* `submission_events.create_event()` is the repo for inserting `SubmissionEvent` rows — used by answer save and question-viewed.
* The integration test file `test_answer_save.py` has helper functions `_setup_core_fixtures()`, `_create_session_row()`, and `_create_envelope_and_context()` that can be reused or referenced for Pass 07 integration test setup.
* Response DB locator columns (`session_locator`, `answer_locator`) contain opaque 32-byte HMAC-SHA256 digests — Pass 07 should verify these are not readable UUIDs.
