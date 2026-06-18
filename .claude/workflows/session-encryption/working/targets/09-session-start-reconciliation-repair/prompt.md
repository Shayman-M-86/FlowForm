# Pass 09: Session-Start Reconciliation Repair

Read `.claude/workflows/session-encryption/working/targets/09-session-start-reconciliation-repair/spec.md` in full before doing anything.

Dependency check: confirm `.claude/workflows/session-encryption/working/pass-reports/08-completion-admin-and-deletion.md` exists and is marked complete. If not, stop.

This pass implements only the committed-core/missing-response-envelope repair path. Do not change the normal session-start rollback path.

Step 1: Inspect the current docs and code paths:

- `docs/session-encryption/06-failure-and-logging-rules.md`
- `docs/session-encryption/02-storage-and-locators.md`
- `docs/session-encryption/03-session-envelope-lifecycle.md`
- `backend/app/services/public_submissions/core/session_starter.py`
- `backend/app/services/public_submissions/core/session_loader.py`
- `backend/app/repositories/core/submission_sessions.py`
- `backend/app/repositories/response/response_envelope_repo.py`
- `backend/tests/integration/response/test_session_start_encryption.py`
- `backend/tests/integration/core/test_session_start_envelope.py`

Step 2: Implement a small service-level reconciliation function, preferably in `backend/app/services/public_submissions/core/reconciliation.py`, that derives session locators from committed core sessions, checks for matching response envelopes, and marks only missing-envelope sessions `abandoned`.

Step 3: Add focused integration tests in `backend/tests/integration/response/test_session_start_reconciliation.py`. Tests must prove rollback and abandoned-session behavior are distinct.

Step 4: Run `bash backend/scripts/run-tests.sh --ai -k "session_start_reconciliation or session_start_encryption"`.

Step 5: Write the pass report to `.claude/workflows/session-encryption/working/pass-reports/09-session-start-reconciliation-repair.md`.

{{context: context/logging-rules.md}}

{{context: context/pass-report-template.md}}
