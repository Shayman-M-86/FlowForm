# Pass 08: Completion, Admin Paths, and Deletion

## Goal

Implement session completion, admin detail/export decrypt paths, and
response-DB-first deletion. These are the remaining service operations
that consume the crypto and repository infrastructure built in earlier passes.

## Files to create or modify

- `backend/app/services/public_submissions/core/completion.py` — new file
- `backend/app/services/results.py` — add admin detail and export decrypt paths (file exists, extend it)

## In scope

### Completion

- Load and lock the current session via the shared session loader
- If already completed: return stored completion state immediately (idempotent — no duplicate effects)
- Load and decrypt all latest revisions via `ResponseAnswerRevisionRepo.get_latest` + `crypto.aes_gcm.decrypt_answer`
- Validate: required questions answered, visible rule paths satisfied, answer shapes valid, cleared states acceptable
- Mark the core session as completed
- Insert a session-completed analytics event
- Reject any later respondent edits (loader enforces this on subsequent calls)

### Admin detail and export

- Authorize project and survey access before touching any response data
- Load core session metadata
- Derive session locator
- Load response envelope
- Load latest revisions (detail) or full revision history (history endpoint)
- Decrypt through the service — never bypass the decrypt path
- Map decrypted question node IDs to the frozen survey version for readable output

### Deletion

- Delete response DB records first, then core records (doc 06)
- If response delete succeeds but core delete fails: mark deletion pending, retry later
- If core delete is attempted first and fails: response data untouched, full retry safe
- Do not claim deletion complete until both stores are handled

## Decisions locked by source docs

- Completion must be idempotent — repeated call returns stored state (doc 03)
- Admin paths must never bypass authorization, locator derivation, or the decrypt service (doc 03)
- Response DB deleted before core DB — response-first ordering is mandatory (doc 06)
- Pending deletions must be marked and retried, not silently dropped (doc 06)

## Out of scope

- Answer save or session loader — pass 06
- Changing upstream authorization logic

## Done when

- [ ] Completion is idempotent: second call returns same state, no duplicate DB writes
- [ ] Admin detail returns decrypted answers mapped to question IDs
- [ ] Deletion removes response DB records before core records
- [ ] Partial deletion failure marks pending and does not claim success
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "completion or admin_decrypt or deletion"`

## Dependencies

Pass 07 (integration tests signed off by operator) must be complete.
