# Pass 05: Session-Start Contract and Reconciliation

## Goal

Close the contract gaps discovered after Pass 04 before later passes build on
session loading and answer saving.

This pass handles the session-start partial where the response envelope commits
but the core session commit fails, removes survey schema from the session-start
response, and aligns the docs/tests with the intended rollback versus abandoned
behavior.

## Files to inspect first

- `docs/session-encryption/01-service-boundary.md`
- `docs/session-encryption/03-session-envelope-lifecycle.md`
- `docs/session-encryption/06-failure-and-logging-rules.md`
- `backend/app/services/public_submissions/core/session_starter.py`
- `backend/app/schema/api/responses/submission_sessions.py`
- `backend/tests/integration/core/test_session_start_envelope.py`
- `backend/tests/integration/core/test_session_start_response_contract.py`
- `backend/tests/e2e/test_submission_session_start.py`
- `backend/tests/e2e/test_submission_session_flows.py`

## In scope

### Response envelope orphan handling

Pass 04 commits the response DB before the core DB. That protects against
returning a resume token before both stores commit, but creates a possible
partial state: response envelope committed, then core commit fails.

Handle this explicitly:

- Catch core commit failure after successful response envelope creation.
- Do not return or set the browser resume token.
- Do not cache the plaintext DEK after a failed core commit.
- Attempt compensating cleanup of the response envelope by `session_locator`.
- If cleanup cannot be guaranteed, document the exact reconciliation target and safe retry/repair path.

The response DB intentionally does not store core IDs, project IDs, survey IDs,
or subject IDs. Any reconciliation design must preserve that privacy boundary.

### Cross-database failure docs

Update `docs/session-encryption/06-failure-and-logging-rules.md` so it names both
session-start partials:

- core session committed, response envelope missing: mark the core session
  abandoned and reconcile;
- response envelope committed, core session missing: delete the orphan envelope
  immediately when possible, otherwise route to reconciliation.

Also keep the existing rule that no browser resume token is exposed until both
stores commit.

### Session-start response contract

Align implementation with `docs/session-encryption/01-service-boundary.md`:

- `POST /submission-session/start` returns only the session-start acknowledgement fields.
- Do not return `survey_schema` from session start, including public-slug starts.
- Keep survey schema delivery in public discovery and link-resolution flows.
- Update OpenAPI/Pydantic response models and all tests that still expect
  `survey_schema` in session-start responses.

### Rollback versus abandoned-session wording

Fix misleading test/report language that says the current pre-commit envelope
failure path marks the core session abandoned. With the Pass 04 ordering, the
normal envelope-failure path rolls back the uncommitted core session.

Only assert abandoned-session behavior for a real committed-core partial.

## Decisions locked by source docs

- No single transaction spans the core and response databases (doc 06).
- Services must explicitly decide authority, secondary failure handling, repair path, and reconciliation path (doc 06).
- Response DB records must not expose core IDs or respondent/project metadata (doc 02).
- Session-start output must not include locators, envelope IDs, key material, or plaintext answer data (doc 01).
- Survey schema delivery belongs to discovery/link-resolution, not session-start acknowledgement (doc 01).

## Out of scope

- Answer save and session loader — pass 06
- Full reconciliation worker implementation unless the immediate cleanup path requires a small repository helper
- Completion, admin reads, and deletion — pass 08
- Changing upstream access, subject resolution, recognition-token policy, or link-resolution policy

## Done when

- [ ] Response-envelope-committed/core-commit-failed session start does not return a resume token.
- [ ] That partial either deletes the response envelope immediately or leaves a documented reconciliation path.
- [ ] Plaintext DEK is not cached when the core commit fails.
- [ ] `docs/session-encryption/06-failure-and-logging-rules.md` names the response-envelope orphan scenario.
- [ ] Session-start responses no longer include `survey_schema`.
- [ ] Tests and comments accurately distinguish rollback from abandoned-session behavior.
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "session_start or submission_session"`

## Dependencies

Pass 04 (session start) must be complete.
