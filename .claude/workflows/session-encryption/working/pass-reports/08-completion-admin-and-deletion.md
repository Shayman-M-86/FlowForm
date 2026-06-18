## Pass report

Pass: 08 — Completion, Admin Paths, and Deletion

Changed files:
* `backend/app/services/public_submissions/core/completion.py` (new)
* `backend/app/services/public_submissions/core/admin_decrypt.py` (new)
* `backend/app/services/public_submissions/core/deletion.py` (new)
* `backend/app/services/results.py` (extended with `DecryptedAnswerResult`, `AdminSessionDetailResult`, `DeletionResult`)
* `backend/app/domain/errors.py` (added `CompletionValidationError`, `DeletionPendingError`)
* `backend/app/repositories/core/submission_sessions.py` (added `mark_completed`)
* `backend/app/repositories/response/response_answer_repo.py` (added `get_all_by_envelope`)
* `infra/postgres/init/templates/response/03-grant-permissions.sql` (added DELETE to grants)
* `backend/tests/integration/core/test_session_start_envelope.py` (updated orphan cleanup test to reflect DELETE permission)
* `backend/tests/integration/response/test_answer_save_encryption.py` (added round-trip decrypt test, removed unused imports)
* `backend/tests/integration/response/test_session_start_encryption.py` (removed unused imports)
* `backend/tests/integration/response/test_completion_encryption.py` (new)
* `backend/tests/integration/response/test_admin_decrypt.py` (new)
* `backend/tests/integration/response/test_deletion_encryption.py` (new)

Behavior implemented:
* Session completion: loads and decrypts all latest revisions, validates required questions from `question_schema.required`, marks core session completed with `completed_at` and `last_activity_at`, inserts `session_completed` analytics event
* Completion idempotency: checks `session_status == "completed"` before locking; returns stored `CompletionResult` immediately without duplicate DB writes
* Admin detail decrypt: derives session locator, loads envelope, unwraps DEK via KMS, decrypts latest revisions, maps question node IDs to question keys from frozen survey version
* Admin history decrypt: same as detail but loads full revision history via `get_history`
* Response-first deletion: deletes envelope (cascade to answers/revisions) and commits response DB before attempting core session delete; raises `DeletionPendingError` if core commit fails after response commit succeeds
* Response DB DELETE grant: added DELETE privilege to `flowform_response_app` user on all response tables, enabling the deletion service and orphan envelope cleanup during session start failures
* Orphan cleanup improvement: `test_core_commit_failure_leaves_orphan_for_reconciliation` updated — compensating delete now succeeds (orphan is cleaned up rather than left for reconciliation)
* Pass 07 test gap: added `test_saved_ciphertext_round_trips_to_original_answer` — verifies saved ciphertext decrypts back to the original answer payload; removed unused imports (`MagicMock`, `DekCache`, `SessionExpiredError`, `SessionInvalidError`)

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "completion or admin_decrypt or deletion"` — 11 passed
* `bash backend/scripts/run-tests.sh --clean-rebuild --ai` — 472 passed (full suite with rebuilt DB, no regressions)

Failures or skipped validation:
* none

Policy change during pass:
* Response DB app user granted DELETE privilege — `infra/postgres/init/templates/response/03-grant-permissions.sql` changed from `SELECT, INSERT, UPDATE` to `SELECT, INSERT, UPDATE, DELETE`. Required by doc 06 deletion ordering. Existing deployments need a manual `GRANT DELETE` or re-run of the init script.

Trace notes:
* entry points touched: `public.py:complete_submission_session` wired to `SessionManagementService.complete_session` → `CompletionService.complete_session`
* service methods touched: `SessionManagementService.complete_session` (wired, was `NotImplementedError`), `CompletionService.complete_session`, `decrypt_session_detail`, `decrypt_session_history`, `delete_session_responses`
* repository helpers touched: `response_answer_repo.get_all_by_envelope`, `submission_sessions.mark_completed`
* side effects changed: completion marks session status to `completed` and inserts `session_completed` event; deletion removes envelope and session rows
* transaction boundary changed or unchanged: completion commits core DB (single commit); deletion commits response DB first then core DB (two commits, ordered)
* tests that now describe behavior: `TestCompletion` (4 tests), `TestAdminDecryptDetail` (2 tests), `TestAdminDecryptHistory` (1 test), `TestDeletion` (4 tests), `test_saved_ciphertext_round_trips_to_original_answer` (1 test)

Remaining risks:

* **Completion validation partial (dependency gap) — documented, deferred:** Spec requires "required questions answered, visible rule paths satisfied, answer shapes valid, cleared states acceptable." Only required-question checking is implemented. No visibility rule evaluator, answer shape validator, or conditional display logic exists anywhere in the codebase — `question_schema` JSONB may contain rules but no engine interprets them. Building these from scratch is a separate feature. Cleared states are accepted (a cleared answer is excluded from the "answered" set, so a required question with only a cleared answer will fail validation). Comment added to `_validate_completion` documenting this gap.
* **Pending deletion not durably persisted — documented, deferred:** Spec says "mark deletion pending, retry later." Current implementation raises `DeletionPendingError` to the caller but does not write a persistent pending-deletion marker — `session_status` CHECK only allows `in_progress`, `completed`, `abandoned`, so adding a deletion state requires a schema migration. Comment added to `deletion.py` documenting this gap. Callers must catch `DeletionPendingError` and track pending deletions externally until that migration lands.
* **Export decrypt path — documented, closed:** `decrypt_session_detail` serves both admin-detail and export use cases. Docstring updated to make this explicit — callers shape the `AdminSessionDetailResult` into CSV/JSON export format.
* **Admin authorization is upstream — documented, closed:** Doc 01 §1 says "It is not responsible for access authorization." Docstring added to `decrypt_session_detail` stating the authorization contract: callers must verify project and survey access before calling. This matches the backend layer convention where services orchestrate and routes authorize.
* **Public completion now wired — closed:** `complete_submission_session` route reads the browser session cookie, delegates to `SessionManagementService.complete_session`, which loads the session via the shared loader (with `allow_completed=True` for idempotency) and calls `CompletionService.complete_session`. The `SessionManagementService.complete_session` stub that raised `NotImplementedError` has been replaced.
* `_get_or_unwrap_dek` helper is duplicated between `completion.py` and `answer_save.py` — could be extracted to a shared helper in a future refactor pass.

## Pass-forward

* `completion.py` is at `backend/app/services/public_submissions/core/completion.py` — `CompletionService.complete_session()` is the entry point for security review.
* `admin_decrypt.py` is at `backend/app/services/public_submissions/core/admin_decrypt.py` — `decrypt_session_detail()` and `decrypt_session_history()` are the admin decrypt paths. Both call `_load_envelope_and_dek` which unwraps DEK via KMS — verify no key material leaks.
* `deletion.py` is at `backend/app/services/public_submissions/core/deletion.py` — `delete_session_responses()` implements response-first ordering with real DELETE on the response DB.
* `DeletionPendingError` in `domain/errors.py` is raised on partial deletion — verify this surfaces correctly and doesn't expose internal state.
* Admin decrypt functions accept `EncryptionSettings` and `SubmissionSession` directly — they do not perform authorization themselves. Security review should confirm that upstream callers enforce project/survey authorization before calling these.
* `_decrypt_revision` in `admin_decrypt.py` rebuilds AAD from stored row metadata — verify the AAD binding is complete (crypto_version, envelope_id, answer_id, answer_locator, revision_id, revision_number).
* Response DB DELETE grant added in this pass — existing deployments need manual `GRANT DELETE ON ALL TABLES IN SCHEMA response_app TO flowform_response_app;` or a re-run of the init template.
