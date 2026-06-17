# Pass 06: Integration Tests — Session Start and Answer Save

## Goal

This is a validation pass. Write and run integration tests that verify the
session start and answer save flows work correctly end-to-end against real
databases and real AWS. The human operator reviews DB state and test output
to confirm correctness before pass 07 begins.

## Human action required

After the agent runs the tests, the operator should:

1. Inspect the response DB directly and confirm: envelopes exist, answer revisions
   are ciphertext (not plaintext), locators are opaque bytes (not UUIDs or question IDs).
2. Confirm the core DB has no plaintext answers and no response DB IDs.
3. Confirm KMS was called for DEK wrap on session start and DEK unwrap on answer save.
4. Sign off before pass 07 starts.

## Test scenarios to cover

### Session start

- Successful start: core session + response envelope both created; resume cookie set
- Envelope creation failure: core session abandoned; no resume cookie returned
- Resumed session: loader finds existing session, returns correct frozen survey version

### Answer save

- First save for a question: revision 1 created, latest pointer set
- Changed answer: revision 2 created, latest pointer updated, revision 1 preserved
- Cleared answer: new revision with null value created
- Duplicate mutation ID: second request returns revision 1 without creating revision 2
- Expired session: rejected before any write
- Completed session: rejected before any write
- Analytics event failure: answer still saved, no error returned to caller

### Concurrency

- Simultaneous first saves for the same question: unique constraint handled, no crash

## Files to create

- `backend/tests/integration/response/test_session_start_encryption.py`
- `backend/tests/integration/response/test_answer_save_encryption.py`

## Done when

- [ ] All scenarios above have passing tests
- [ ] Response DB rows contain only opaque bytes in locator columns — no UUIDs or question IDs visible
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "session_start_encryption or answer_save_encryption"`
- [ ] Operator has reviewed DB state and signed off

## Dependencies

Pass 05 (answer save and session loader) must be complete.
