# Pass 04: Session Start

## Goal

Wire response envelope creation into the existing session starter so that a
submission session is only considered started when both the core session record
and the response envelope exist. The raw browser resume token must not be
returned until both stores have committed.

## Existing file to modify

- `backend/app/services/public_submissions/core/session_starter.py`

## What currently exists there

The session starter creates a core submission session and returns a resume token.
It does not yet create a response envelope or know about encryption.

## In scope

- After the core session is created, derive the session locator using `crypto.locators`
- Generate a fresh DEK, wrap it with KMS using `crypto.kms.wrap_dek`
- Create the response envelope using `ResponseEnvelopeRepo.create`
- Cache the plaintext DEK in `DekCache` keyed by session locator
- Only set / return the browser resume cookie after both commits succeed
- If response envelope creation fails: roll back or mark the core session abandoned; add it to the reconciliation list
- Single-use link consumption and recognition-token side effects must not commit if envelope creation fails (doc 06)

## Failure handling locked by source docs

- Do not expose the resume token until core + response both exist (doc 03, doc 06)
- If core session committed but envelope failed: mark core session abandoned, do not retry silently (doc 06)
- Single-use link and recognition-token side effects roll back with the session (doc 06)

## Out of scope

- Answer save, session loader, completion — passes 05 and 07
- Admin reads or deletion
- Changing the upstream access/subject resolution logic

## Done when

- [ ] Resume token is never returned when envelope creation fails
- [ ] Core session is marked abandoned when envelope creation fails after core commit
- [ ] Integration test covers: successful start (both DBs have records), envelope failure rolls back token, abandoned session cannot be resumed
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "session_start"`

## Dependencies

Passes 01, 02, and 03 must be complete (crypto helpers, response repos, KMS wiring).
