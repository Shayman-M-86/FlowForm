## Pass report

Pass: 05 — Session-Start Contract and Reconciliation

Changed files:

* `backend/app/services/public_submissions/core/session_starter.py` — core commit failure handling, survey_schema removal
* `backend/app/repositories/response/response_envelope_repo.py` — added `delete_by_locator`
* `backend/app/schema/api/responses/submission_sessions.py` — removed `survey_schema` field
* `docs/session-encryption/06-failure-and-logging-rules.md` — documented both session-start partial states, added orphan envelope reconciliation target
* `backend/tests/integration/core/test_session_start_envelope.py` — fixed rollback vs abandoned language, added core-commit-failure tests
* `backend/tests/integration/core/test_session_start_response_contract.py` — updated to assert survey_schema absent
* `backend/tests/e2e/test_submission_session_start.py` — removed survey_schema from expected response body
* `backend/tests/e2e/test_submission_session_flows.py` — removed survey_schema assertions
* `backend/tests/unit/test_submission_session_contracts.py` — removed survey_schema from expected serialization

Behavior implemented:

* Core commit failure after response envelope creation: does not return resume token, does not cache DEK, attempts best-effort orphan envelope deletion, raises `SessionStartError`.
* Orphan envelope cleanup is best-effort — the response DB app user lacks DELETE permission, so failed cleanup is logged and the orphan becomes a reconciliation target.
* `survey_schema` removed from `PublicSubmissionSessionResponses` — session start returns only acknowledgement fields (status, started_at, expires_at, survey_version_id). Schema delivery belongs to discovery/link-resolution flows.
* Doc 06 now explicitly names both session-start partial states and lists orphan envelopes as a reconciliation target.
* Test language corrected: pre-commit envelope failures are "rolled back" (not "abandoned"); only a committed core session without an envelope is "abandoned".

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "session_start or submission_session"` — 49 passed

Failures or skipped validation:

* none

Policy change during pass:

* Updated `docs/session-encryption/06-failure-and-logging-rules.md`: added "Session start partial states" subsection and "response envelopes without core sessions" to reconciliation targets.

Trace notes:

* entry points touched: `SessionStarter.start()` in `session_starter.py`
* service methods touched: `SessionStarter.start()`, `SessionStarter._compensate_orphan_envelope()` (new)
* repository helpers touched: `response_envelope_repo.delete_by_locator()` (new)
* side effects changed: core commit failure now triggers compensating envelope cleanup attempt
* transaction boundary changed: core commit now wrapped in try/except; on failure, compensating response DB delete + commit attempted

Remaining risks:

* `delete_by_locator` will fail at runtime because the response DB app user has only SELECT/INSERT/UPDATE (no DELETE). The cleanup path handles this gracefully. A future reconciliation worker with elevated privileges will handle orphan envelope deletion.
* No reconciliation worker exists yet — orphan envelopes accumulate until one is built (pass 08+ scope).

## Pass-forward

* `SessionStarter.start()` now raises `SessionStartError("Core commit failed after response envelope creation")` when the core commit fails after response envelope creation — downstream error handlers should expect this variant.
* `PublicSubmissionSessionResponses` no longer has a `survey_schema` field. Session-start responses contain only `status`, `started_at`, `expires_at`, `survey_version_id`.
* `response_envelope_repo.delete_by_locator(db, session_locator)` exists but will fail with the app user's permissions. Reconciliation or admin cleanup paths need elevated DB credentials.
* `_compensate_orphan_envelope` logs `session_start.orphan_envelope_cleanup_failed` at `critical` level (with traceback via `exc_info=True`) when cleanup fails — the session loader should not expect every envelope to have a matching core session.
* Doc 06 now documents both session-start partial states; the session loader's error handling should align with these documented scenarios.
* The response DB app user permissions (no DELETE) are defined in `infra/postgres/init/templates/response/03-grant-permissions.sql`.

## Post-pass hardening addendum

Additional changes applied after reviewing the pass report from the failure-boundary and route-contract angles:

Changed files:

* `backend/app/services/public_submissions/core/session_starter.py` — `_compensate_orphan_envelope()` now rolls back the response DB session if best-effort cleanup fails, so a failed DELETE/commit does not leave the SQLAlchemy session in a failed transaction.
* `backend/tests/integration/core/test_session_start_envelope.py` — added response-commit failure coverage, compensation locator coverage, and failed-compensation rollback/logging coverage.
* `backend/tests/e2e/test_submission_session_start.py` — added route-level failure coverage proving session-start aborts do not set submission-session or recognition cookies.

Behavior hardened:

* Response DB commit failure during envelope creation is treated as a pre-core-commit envelope failure: the core session is rolled back, the response envelope is rolled back, no resume token is returned, and `SessionStartError("Failed to create response envelope")` is raised.
* Core commit failure after a committed response envelope now has an explicit test proving compensation receives the exact persisted `session_locator`.
* Failed orphan-envelope compensation now rolls back the response DB session before logging `session_start.orphan_envelope_cleanup_failed`.
* The public `POST /api/v1/public/submission-session/start` route now has e2e coverage proving cookies are only set after the service returns successfully.

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "session_start or submission_session"` — 53 passed, 379 deselected
* `git diff --check -- backend/app/services/public_submissions/core/session_starter.py backend/tests/integration/core/test_session_start_envelope.py backend/tests/e2e/test_submission_session_start.py` — passed

Remaining risks after hardening:

* `delete_by_locator` still fails for the normal response DB app user because that role lacks DELETE permission. The failure path now rolls back the response DB session cleanly and logs the reconciliation signal.
* No reconciliation worker exists yet — orphan envelopes remain a pass 08+ target.

## Convention cleanup

Additional changes applied to align `session_starter.py` with service conventions.

Changed files:

* `backend/app/services/public_submissions/core/session_starter.py` — convention fixes only; no behavior changes.

Changes applied:

* Collapsed duplicate `except (KmsError, LinkageSecretError)` / `except Exception` blocks in `_create_response_envelope` into a single `except Exception` — the specific catch was dead code since the generic handler did the same thing. Removed unused `KmsError` and `LinkageSecretError` imports.
* Replaced `session: object` parameter + runtime `assert isinstance(session, SubmissionSession)` with a proper `session: SubmissionSession` type hint via `TYPE_CHECKING` import, consistent with peer services.
* Removed redundant try/except wrapper around `_create_response_envelope()` in `start()` — that method already rolls back core and raises `SessionStartError`, so the outer handler was unreachable dead code.
* Added `exc_info=True` to all `logger.error` calls so tracebacks are captured.
* Escalated `_compensate_orphan_envelope` failure log from `logger.error` to `logger.critical` — a leaked orphan envelope with no alarm warrants higher severity.

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "session_start"` — 18 passed
