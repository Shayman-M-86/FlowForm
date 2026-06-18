## Pass report

Pass: 07 — Integration Tests — Session Start and Answer Save

Changed files:
* `backend/tests/integration/response/test_session_start_encryption.py` (new)
* `backend/tests/integration/response/test_answer_save_encryption.py` (new)

Behavior implemented:
* Session start integration tests: successful start creates core session + response envelope with resume cookie, KMS failure rolls back core session with no resume cookie, resumed session loader finds existing session with correct frozen survey version, session locator verified as opaque 32-byte HMAC digest
* Answer save integration tests: first save creates revision 1 with latest pointer, changed answer creates revision 2 preserving history, cleared answer creates revision with null value, duplicate mutation ID returns existing without new revision, expired session rejected at loader level, completed session rejected at loader level, analytics event failure does not block answer save, concurrent saves handled without crash
* Verified response DB locator columns (`session_locator`, `answer_locator`) contain opaque 32-byte HMAC-SHA256 digests — not readable UUIDs or question IDs

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "session_start_encryption or answer_save_encryption"` — 22 passed (originally 17; 5 added in amendment)
* `bash backend/scripts/run-tests.sh --ai` — 477 passed (full suite, no regressions)

Skipped/outstanding validation:
* **Real AWS/KMS not tested:** All tests patch `wrap_dek`, `unwrap_dek`, and `get_linkage_secret`. They prove the call contracts (mock assertions verify wrap/unwrap are called with correct arguments) but do not exercise real KMS. Real AWS validation requires operator-level infrastructure and is out of scope for integration tests.
* **Operator sign-off not completed:** Spec requires human DB inspection and sign-off. This has not yet been performed.
* **True concurrency not tested:** The `TestSequentialDuplicateSaves` class (renamed from `TestConcurrentFirstSaves`) covers sequential duplicate/update behavior. True concurrent testing (parallel threads/processes with separate DB sessions) is a known gap — it requires multi-threaded test infrastructure not currently in scope.
* **Committed-core/missing-envelope reconciliation:** Deferred to Pass 09 (`session-start-reconciliation-repair`).

Policy change during pass:
* none

Trace notes:
* entry points touched: none (test-only pass)
* service methods touched: none
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior:
  - `TestSuccessfulSessionStart.test_creates_core_session_and_response_envelope`
  - `TestSuccessfulSessionStart.test_session_locator_is_opaque_32_bytes`
  - `TestSuccessfulSessionStart.test_resume_cookie_set_on_success`
  - `TestEnvelopeCreationFailure.test_kms_failure_rolls_back_core_session`
  - `TestResumedSession.test_loader_finds_existing_session`
  - `TestResumedSession.test_loader_returns_correct_frozen_survey_version`
  - `TestResumedSession.test_loader_rejects_invalid_token`
  - `TestFirstSave.test_first_save_creates_revision_1`
  - `TestFirstSave.test_locator_columns_are_opaque_bytes`
  - `TestFirstSave.test_saved_ciphertext_round_trips_to_original_answer`
  - `TestChangedAnswer.test_changed_answer_creates_revision_2`
  - `TestClearedAnswer.test_cleared_answer_creates_revision_with_null_value`
  - `TestDuplicateMutationId.test_duplicate_mutation_id_returns_existing`
  - `TestExpiredSession.test_expired_session_rejected`
  - `TestCompletedSession.test_completed_session_rejected`
  - `TestAnalyticsFailure.test_analytics_event_failure_does_not_block_save`
  - `TestSequentialDuplicateSaves.test_sequential_duplicate_saves_handled`
  - `TestSuccessfulSessionStart.test_wrap_dek_called_on_session_start` (amendment)
  - `TestClearedAnswer.test_cleared_revision_decrypts_to_cleared_state` (amendment)
  - `TestCoreDbPrivacy.test_core_db_has_no_plaintext_answers_or_response_ids` (amendment)
  - `TestCacheMissUnwrapDek.test_unwrap_dek_called_on_cache_miss` (amendment)
  - `TestCacheMissUnwrapDek.test_unwrap_dek_not_called_on_cache_hit` (amendment)

Remaining risks:
* Terminology note: the KMS/envelope failure test covers the normal pre-core-commit path, where the uncommitted core session is rolled back. It is not an abandoned-session case. `abandoned` is reserved for a committed core session that cannot safely resume, such as a reconciliation-discovered core session without a response envelope.
* Expired/completed session tests verify rejection at the session loader level (not at the `AnswerSaveService` level). The service's step 1 only checks `session_status != "in_progress"` — expiry is enforced by the loader. This is correct per the architecture but worth noting.
* Sequential duplicate test (renamed from `TestConcurrentFirstSaves`) covers two saves in sequence, not truly concurrent (parallel threads). True concurrent testing would require multi-threaded or multi-process test infrastructure not currently in scope.

---

## Amendment — 2026-06-18

This amendment corrects gaps identified in the original pass report.

Changed files:
* `backend/tests/integration/response/test_session_start_encryption.py` (1 test added)
* `backend/tests/integration/response/test_answer_save_encryption.py` (4 tests added, 1 class renamed)

Fixes applied:

1. **Cleared-answer ciphertext now fully verified:** `test_cleared_revision_decrypts_to_cleared_state` decrypts the cleared revision's ciphertext and asserts `answer_state="cleared"` and `answer_value=None`. Previously the cleared test only checked revision creation and null-state behavior without decrypting.

2. **Core DB privacy checks added:** `test_core_db_has_no_plaintext_answers_or_response_ids` asserts that after answer save, neither the core `submission_sessions` row nor any `submission_events` rows contain the plaintext answer value or the response envelope ID in any column.

3. **KMS wrap_dek assertion added:** `test_wrap_dek_called_on_session_start` uses `MagicMock` for `wrap_dek` and asserts it was called exactly once with a 32-byte DEK. This proves the session start path invokes KMS wrapping (mocked) with correct arguments.

4. **Cache-miss unwrap_dek assertion added:** `test_unwrap_dek_called_on_cache_miss` creates an `AnswerSaveService` with an empty `DekCache` and verifies `unwrap_dek` is called with the envelope's `wrapped_dek`. `test_unwrap_dek_not_called_on_cache_hit` verifies the cache-hit path skips `unwrap_dek` entirely.

5. **Concurrent test renamed:** `TestConcurrentFirstSaves` renamed to `TestSequentialDuplicateSaves` and test method renamed to `test_sequential_duplicate_saves_handled` to accurately describe the sequential (not concurrent) nature of the test.

6. **Report honesty fix:** "Failures or skipped validation: none" replaced with "Skipped/outstanding validation" section listing: real AWS/KMS not tested, operator sign-off not completed, true concurrency not tested, reconciliation deferred to Pass 09.

Still outstanding (not code-fixable in this pass):
* **Real AWS/KMS validation:** Tests mock all KMS calls. Real AWS requires operator infrastructure.
* **Operator sign-off:** Requires human DB inspection per spec.
* **True concurrency:** Requires multi-threaded test infrastructure.

Tests run (post-amendment):
* `bash backend/scripts/run-tests.sh --ai -k "session_start_encryption or answer_save_encryption"` — 22 passed
* `bash backend/scripts/run-tests.sh --ai` — 477 passed (full suite, no regressions)

## Pass-forward

* Integration test files are `backend/tests/integration/response/test_session_start_encryption.py` and `backend/tests/integration/response/test_answer_save_encryption.py` — reference for test setup patterns.
* `_setup_core_fixtures()` creates user/project/store/survey/version/question in one call — reusable for pass 08 tests.
* `_create_session_row()` uses raw SQL to set expired/completed states that satisfy DB CHECK constraints (`ck_submission_sessions_expires_at_after_started_at`, `ck_submission_sessions_completed_at_consistent`, `ck_submission_sessions_completed_before_last_activity`).
* `_create_envelope_and_context()` builds a `SessionContext` with real HMAC-derived `session_locator` using `derive_session_locator()` — not random bytes. Pass 08 completion tests should use the same pattern.
* `_LINKAGE_SECRET = b"\xcc" * 32` is the test linkage secret used across answer save tests — patch `get_linkage_secret` to return it when testing services that derive locators.
* Crypto patches for `AnswerSaveService`: patch `app.services.public_submissions.core.answer_save.get_linkage_secret` and `derive_answer_locator`. For `SessionStarter`: patch `app.services.public_submissions.core.session_starter.get_linkage_secret` and `wrap_dek`.
* `load_current_session()` needs its own crypto patch at `app.services.public_submissions.core.session_loader.get_linkage_secret`.
