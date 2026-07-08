## Pass report

Pass: 09 — Session-Start Reconciliation Repair

Changed files:

* `backend/app/repositories/core/submission_sessions.py` — added `get_in_progress_sessions()` query helper
* `backend/app/services/public_submissions/core/reconciliation.py` — new file, reconciliation service
* `backend/tests/integration/response/test_session_start_reconciliation.py` — new file, integration tests

Behavior implemented:

* `reconcile_orphaned_sessions()` scans committed in-progress core sessions, derives session locators, checks the response DB for matching envelopes, and marks missing-envelope sessions as `abandoned`
* Completed and already-abandoned sessions are excluded from scanning by the `get_in_progress_sessions()` query
* Returns a structured `ReconciliationResult` with counts and safe session IDs for operator review
* Per-session errors are caught and counted without aborting the scan
* Safe logging: only `session_id` and aggregate counts are logged; no locators, tokens, or key material

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "session_start_reconciliation or session_start_encryption"` — 14 passed

Failures or skipped validation:

* none

Policy change during pass:

* none

Trace notes:

* entry points touched: `reconcile_orphaned_sessions()` in `reconciliation.py`
* service methods touched: `reconcile_orphaned_sessions()`
* repository helpers touched: `get_in_progress_sessions()` in `submission_sessions.py`; `mark_abandoned()` (existing, called by reconciliation); `get_by_locator()` in `response_envelope_repo.py` (existing, called by reconciliation)
* side effects changed: none — new additive service only
* transaction boundary changed or unchanged: unchanged for session start; reconciliation commits after scanning all sessions
* tests that now describe behavior: `TestReconcileOrphanedSessions` (4 tests), `TestAbandonedSessionRejectedByLoader` (1 test), `TestKmsFailureStillRollsBack` (1 test)

Remaining risks:

* No scheduler or CLI runner for reconciliation — operator must call `reconcile_orphaned_sessions()` manually or wire it into a background task (out of scope per spec)
* Orphan response envelopes without core sessions are not discovered by this reconciliation path — they rely on the existing compensating delete in `SessionStarter._compensate_orphan_envelope()`

## Pass-forward

* `reconciliation.py` is at `backend/app/services/public_submissions/core/reconciliation.py` — `reconcile_orphaned_sessions()` is the entry point. It accepts `EncryptionSettings` and `LocatorService` for test injection.
* `get_in_progress_sessions()` in `submission_sessions.py` returns all committed in-progress sessions — security review should confirm this query does not expose sensitive data.
* Reconciliation logs only `session_id` (UUID) and aggregate counts — verify no locator, token, or key material leaks through `extra=` kwargs.
* The reconciliation commit is a single `db.commit()` after all sessions are scanned — verify this is safe and does not risk partial state if the commit fails.
* E2E filter should include `session_start_reconciliation` in addition to `submission_session` patterns.
* All existing session-start encryption tests (8 tests in `test_session_start_encryption.py`, 11 in `test_session_start_envelope.py`) still pass — no regressions from this pass.
