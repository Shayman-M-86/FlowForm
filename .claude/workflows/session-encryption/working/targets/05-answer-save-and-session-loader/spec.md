# Pass 05: Answer Save and Session Loader

## Goal

Implement the shared current-session loader and the answer save flow.
The loader is used by answer save, question-viewed events, and completion.
Answer save must follow the exact 12-step sequence from doc 03.

## Files to create

- `backend/app/services/public_submissions/core/session_loader.py` — shared loader
- `backend/app/services/public_submissions/core/answer_save.py` — answer save orchestration

## In scope

### Session loader

Shared by answer save, question-viewed, and completion. It must:

- Read the browser resume cookie
- Hash the raw resume token
- Load the core session by token hash
- Load the frozen survey version
- Reject: missing, expired, abandoned, invalid, or completed sessions when editing
- Derive the session locator
- Load the response envelope
- Return a safe service context (no internal IDs, locators, key material exposed to caller)

### Answer save — exact 12-step sequence (doc 03)

1. Validate and lock the current session
2. Check mutation ID — if revision already exists for this logical answer, return it immediately
3. Validate the answer against the frozen survey version
4. Derive the session locator and answer locator
5. Load the response envelope
6. Load plaintext DEK from DekCache; on miss, unwrap with KMS and cache
7. Encrypt the answer payload using `crypto.aes_gcm` with fresh nonce and AAD
8. Insert a new immutable revision via `ResponseAnswerRevisionRepo.create`
9. Update the latest pointer via `ResponseAnswerRevisionRepo.update_latest_pointer`
10. Commit the response transaction
11. Insert the core answer-saved analytics event
12. Commit the core transaction

If step 12 fails, the answer is still considered saved — analytics is secondary (doc 06).

### Question-viewed event

Validate the question belongs to the frozen survey version, write to core event log.
Failure must not block the respondent (doc 03).

## Decisions locked by source docs

- Mutation ID check at step 2 — before locking the logical answer row (doc 03, doc 04)
- Response write is authoritative; analytics event failure does not un-save the answer (doc 06)
- Loader must not expose locators, key material, envelope ID, or session ID to browser (doc 01, doc 03)
- Frontend validation is not trusted — backend must validate against frozen survey version (doc 04)

## Out of scope

- Completion — pass 07
- Admin reads or deletion — pass 07

## Done when

- [ ] Session loader rejects all forbidden states correctly
- [ ] Answer save follows all 12 steps in order
- [ ] Mutation ID dedup returns existing revision without creating a duplicate
- [ ] Analytics event failure does not cause an error response
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "answer_save or session_loader"`

## Dependencies

Pass 04 (session start) must be complete — loader depends on sessions existing.
