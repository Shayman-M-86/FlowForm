# Pass 09: Session-Start Reconciliation Repair

## Goal

Implement the committed-core/missing-response-envelope reconciliation path
documented in `docs/session-encryption/06-failure-and-logging-rules.md`.

This pass closes the abandoned-session ambiguity from earlier passes:

- pre-core-commit envelope failure rolls back and must not be marked abandoned;
- committed core session with no response envelope is a repair state and must be
  marked `abandoned`;
- response envelope without core session remains an orphan-envelope cleanup path.

## Files to create or modify

- `backend/app/services/public_submissions/core/reconciliation.py` - new file
- `backend/app/repositories/core/submission_sessions.py` - use the existing
  `mark_abandoned()` helper and add only small query helpers if needed
- `backend/tests/integration/response/test_session_start_reconciliation.py` - new
  focused integration tests
- `docs/session-encryption/06-failure-and-logging-rules.md` - update only if the
  implementation reveals a doc gap

## In scope

### Core-session-without-envelope repair

Add a service-layer reconciliation function that:

- scans committed core submission sessions that are still `in_progress`;
- derives each session locator from the core session ID and linkage secret;
- checks the response DB for a matching response envelope by locator;
- calls `submission_sessions.mark_abandoned()` for committed core sessions whose
  envelope is missing;
- leaves sessions unchanged when a matching response envelope exists;
- leaves completed and already-abandoned sessions unchanged;
- returns a small structured result with counts and safe identifiers for operator
  review.

### Privacy boundary

The reconciliation design must preserve the response DB privacy boundary:

- do not add core IDs, project IDs, survey IDs, link IDs, subject IDs, or user IDs
  to response DB rows;
- do not use response DB data to reconstruct core identities;
- do not log raw browser tokens, linkage secrets, locators, ciphertext, nonces, or
  key material;
- only derive locators from core-side committed sessions and query response by the
  derived opaque locator.

### Existing session-start behavior

Do not change the normal `SessionStarter` failure behavior:

- KMS/envelope failure before core commit still rolls back the uncommitted core
  transaction;
- response-envelope-committed/core-commit-failed still attempts orphan-envelope
  cleanup by `session_locator`;
- `mark_abandoned()` is not called from the normal pre-core-commit failure path.

## Tests to add

- In-progress committed core session with no response envelope is marked
  `abandoned`.
- In-progress committed core session with a matching response envelope remains
  `in_progress`.
- Completed and already-abandoned core sessions are ignored.
- A repaired abandoned session is rejected by the current-session loader.
- The normal KMS/envelope failure test still asserts rollback, not abandoned.

## Decisions locked by source docs

- `abandoned` is reserved for a committed core session that can no longer be
  safely resumed (doc 06).
- Response DB records must not expose core IDs or respondent/project metadata
  (doc 02).
- Current-session loading rejects abandoned sessions (doc 03).
- No browser resume token is exposed until both core and response records commit
  (doc 06).

## Out of scope

- A scheduler, CLI, or background worker for running reconciliation repeatedly.
- Schema changes, pending-repair tables, or response-side core-ID columns.
- Orphan response-envelope discovery beyond the immediate cleanup path already
  implemented by session start.
- Completion, admin decrypt, deletion, and export behavior.

## Done when

- [ ] A service-level reconciliation function marks committed core sessions
      without envelopes as `abandoned`.
- [ ] Tests prove rollback and abandoned-session behavior are distinct.
- [ ] Tests prove matched-envelope, completed, and already-abandoned sessions are
      not modified.
- [ ] Privacy boundary is preserved: no core identifiers are added to response
      DB rows.
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "session_start_reconciliation or session_start_encryption"`

## Dependencies

Pass 08 (completion, admin, deletion) must be complete.
