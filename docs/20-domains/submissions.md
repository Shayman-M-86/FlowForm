---
title: Submissions
aliases:
  - "Submissions"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [backend]
related_code:
  - "../../backend/app/services/public_submissions/"
  - "../../backend/app/schema/orm/core/submission_session.py"
  - "../../backend/app/schema/orm/core/submission_answer_slot.py"
  - "../../backend/app/api/v1/respondent/submission_sessions.py"
  - "../../backend/tests/e2e/test_submission_session_flows.py"
  - "../../backend/tests/integration/core/test_answer_save.py"
related_docs:
  - "Links and subjects"
  - "Surveys and versioning"
  - "Responses and encryption"
  - "Data flows"
---

# Submissions

Defines one respondent attempt against an exact survey version and coordinates
its core metadata with encrypted response storage. In current persistence there
is no standalone `submissions` table; the submission session is the aggregate
root for the attempt.

## Purpose

The domain gives a respondent a resumable, expiring attempt whose answers can be
saved incrementally without placing plaintext answer values in core data. It
also preserves the survey version, subject, access link, events, and response
destination needed to interpret or administer that attempt later.

## Responsibilities

- Resolve respondent access and subject context before creating an attempt.
- Create a core submission session and a corresponding encrypted response
  envelope, returning browser and recognition cookies where required.
- Validate the browser session token, expiry, lifecycle state, and frozen survey
  version for later commands.
- Validate each answer against its question family, create one stable core
  answer slot per session/question, and upsert the encrypted current answer in
  the response database.
- Record question-viewed, answer-saved, and session-completed events as core
  metadata. The schema also recognizes a `session_started` event type.
- Move an attempt from `in_progress` to `completed`, or mark an unrecoverable
  in-progress session `abandoned` during reconciliation.

## Non-responsibilities

- The domain does not authenticate or authorize Studio results access.
- It does not define survey nodes or choose which version is publishable.
- It does not store plaintext answers, wrapped survey keys, or direct respondent
  identifiers in the response database.
- The browser form filler decides rule navigation and when a respondent is ready
  to complete; backend limits are described under verified gaps.

## Main entities and invariants

| Entity | Role | Important invariant |
| --- | --- | --- |
| Submission session | Core attempt metadata | Status is `in_progress`, `completed`, or `abandoned`; expiry follows start; completion status and timestamp agree. |
| Browser session token | Cookie-held resume credential | Generated randomly, stored only as a unique hash, and resolved to one session. |
| Submission answer slot | Core pointer for one session/question | Unique for the pair and constrained to the session's exact survey version; contains no answer value. |
| Submission event | Core analytics fact | Question events require a question in the same version; session events carry no question. |
| Response envelope/answer | Encrypted response-side records | Reached through opaque locators, not cross-database foreign keys. |

Every session belongs to one project survey, one version of that survey, one
project response store, and optionally one link and subject from the same scope.
Answer mutations lock the core session and reject states other than
`in_progress` before persisting data.

## Important workflows

1. Session start validates a public slug or link, resolves subject/token actions,
   creates core state, derives an opaque locator, commits the response envelope,
   then commits the core transaction and sets cookies.
2. A later command hashes the browser token, loads or builds the session crypto
   context, and rejects missing, expired, abandoned, or disallowed completed
   sessions.
3. Answer save locks the session, verifies the question belongs to the frozen
   version, validates the typed value, creates the core slot, encrypts the
   payload, commits the slot, and then upserts response ciphertext.
4. Question-viewed and answer-saved events are best-effort analytics around the
   attempt; answer persistence does not depend on the later analytics write.
5. Completion locks and transitions the core session, records a best-effort
   completion event, commits, and evicts the cached write context.
6. Reconciliation scans in-progress core sessions and marks those without a
   matching response envelope as abandoned.

The cross-store sequence is shown in [[data-flows|Data flows]] and the key/data
boundary in [[responses-and-encryption|Responses and encryption]].

## Implementation map

- `backend/app/services/public_submissions/api/session_management.py` is the
  respondent-facing lifecycle facade.
- `backend/app/services/public_submissions/core/actions/` owns start, answer
  save, event, and completion orchestration.
- `backend/app/services/public_submissions/core/session_loader.py` resolves the
  hashed resume token and builds the cached crypto context.
- `backend/app/services/public_submissions/core/reconciliation.py` implements
  the one-way missing-envelope repair pass.
- Core session, event, and slot mappings live under
  `backend/app/schema/orm/core/`; response mappings and crypto are owned by the
  adjacent response domain.
- E2E and integration tests cover representative entry, answer, completion,
  encryption, compensation, and reconciliation behavior.

## Verified gaps and open questions

- Core and response writes use independent transactions. Session start has
  compensating envelope deletion, but failed compensation leaves a response
  orphan that the current core-to-response reconciler cannot discover.
- Answer save commits the core slot before the response upsert; a later response
  failure can leave a slot with no encrypted answer. No repair job for this
  direction was found.
- Completion validates session state but does not independently require answers
  for every rule-derived required question. That policy currently lives only in
  the frontend filler.
- The cached session context checks token and expiry but does not re-read status
  until cache miss/eviction; cross-worker state changes can remain stale for the
  cache lifetime.
- Reconciliation exists as a callable service, but no checked-in scheduler or
  operator workflow invoking it was found.
- `session_started` is a valid database event type, but the inspected session
  start path does not create that event.
- The meaning of “submission” for abandoned and incomplete attempts is not yet
  fixed in product terminology or retention policy.

## Related documents

- [[links-and-subjects|Links and subjects]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[responses-and-encryption|Responses and encryption]]
- [[data-flows|Data flows]]
