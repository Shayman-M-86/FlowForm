# Remaining Work  -  Session/Response Encryption

Consolidated view of what's left, derived from the prior implementation
checklist Phase 3 onward, the `TODO(phase*)` markers in
`app/api/v1/public.py`, and the session-service open-issues audit.

## Status summary

Phase 1 (schema) is done. Phase 2 (API contracts  -  public and admin route
stubs) is done. Phase 2.5 (subject access model) is mostly done:
`SessionStarter`, `ProjectSubjectResolver`, and `SurveyAccessResolver` are
real, integration-tested services. The session-start service is real  -  it
resolves access (public slug or link token), resolves the optional subject
from server-owned context, binds one survey version, and generates/hashes a
browser session token. What remains is everything downstream of session
start: response envelopes, resume, answer revisions, completion, real
cryptography, admin reads, frontend integration, and hardening.

## Phase 3 remainder  -  service skeleton without real crypto

**Repositories**
- [ ] Core event repository
- [ ] Response envelope repository
- [ ] Response answer repository
- [ ] Response revision repository

**Services**
- [ ] Session resume service
- [ ] Answer save service
- [ ] Completion service
- [ ] Admin response read service

**Session start  -  remaining pieces**
- [ ] Create a response envelope as part of session start
- [ ] Return the raw browser token only after both the core and response
      stores succeed

**Session resume**
- [ ] Hash the browser token
- [ ] Load an in-progress session
- [ ] Reject expired, completed, or abandoned sessions
- [ ] Return current canonical answers when available

**Temporary crypto interfaces (dev implementations)**

Define final method signatures/shapes now, backed by deterministic fake
locators and reversible placeholder ciphertext until Phase 6:
- [ ] Linkage secret provider
- [ ] Locator service
- [ ] DEK provider
- [ ] Answer cipher
- [ ] AAD builder

**`public.py` placeholders to replace**
- [ ] `public.py:165` `TODO(phase3)`  -  current-session route returns a
      placeholder; needs a real session lookup (via the resume service)
- [ ] `public.py:203` `TODO(phase3)`  -  question-viewed event route is a
      placeholder; needs real persistence via the core event repository

## Phase 4-5

### Phase 4  -  answer revision mechanics
- [ ] Validate answers against the frozen survey version
      (`public.py:179` `TODO(phase4)`)
- [ ] First-save: derive/fake `answer_locator`, create `response_answers`,
      create revision 1, set `latest_revision_id`, record `answer_saved`
      event after the response write commits
- [ ] Changed-answer save: find the logical answer by
      `(envelope_id, answer_locator)`, insert the next immutable revision,
      update the latest pointer
- [ ] Clear-answer save as a new revision, not a deletion
- [ ] `client_mutation_id` idempotency (if part of the route contract)
- [ ] Concurrency handling for simultaneous first saves and simultaneous
      updates

### Phase 5  -  completion and session lifecycle
- [ ] Question-viewed events
- [ ] Completion (`public.py:218` `TODO(phase5)`): validate required
      canonical answers, set status to `completed`, set `completed_at`,
      reject further respondent edits
- [ ] Abandonment/expiry: reject writes to expired sessions, provide a
      maintenance path for stale in-progress sessions, define
      preserve-vs-delete retention rules for partial responses

## Phase 6  -  real cryptography

- [ ] Implement real cryptography (HMAC-SHA-256 locators, KMS-backed DEKs,
      AES-256-GCM answer encryption with per-revision nonces, stable AAD,
      linkage-secret and DEK caching, key rotation). Full design is in
      [cryptography-plan.md](cryptography-plan.md)  -  not re-described here.

## Phase 7-9

### Phase 7  -  admin reads, export, and deletion
- [ ] Wire the admin response read service (list/detail/history/export/delete
      are currently contract-only placeholders in the admin responses route)
- [ ] Decrypt path for admin detail/history/export, validated against
      locators
- [ ] Delete: tombstone or remove core session metadata, remove response
      envelope and cascading rows, handle pending-deletion when one database
      succeeds and the other fails
- [ ] Privileged-access audit logging without plaintext answers

### Phase 8  -  frontend integration
- [ ] Public Site: move from one-shot submit to start/resume a session,
      save answers incrementally, complete via the completion route, and
      handle expired/completed/abandoned/invalid session responses
- [ ] Studio: update results views to the new admin response routes
- [ ] Remove frontend assumptions that a submission is created only once at
      final submit

### Phase 9  -  verification and hardening
- [ ] Cross-database failure tests (core write succeeds + response envelope
      fails; response answer succeeds + analytics event fails; KMS fails;
      Secrets Manager fails on cache miss; response DB unavailable)
- [ ] Reconciliation tasks: core sessions without response envelopes, stale
      session-initialization failures, pending deletions, inconsistent
      linkage-key versions, missing response envelopes during admin reads
- [ ] Metrics for session starts, answer saves, completions, decrypt
      failures, KMS failures, reconciliation repairs
- [ ] Sanitize logs and Sentry payloads (no plaintext answers, browser
      tokens, plaintext DEKs, or raw linkage secrets)
- [ ] IAM/KMS policy documentation
- [ ] Key-rotation runbook

## Open decisions

From the session-service open-issues audit:

- **Anonymous-subject-creation policy**  -  `ProjectSubjectResolver` has a
  `create_anonymous_subject` branch marked `TODO(subject-policy)` that is
  dead in production (`SessionStarter` always passes `False`). Blocked on a
  product decision about when anonymous access should create a
  `project_subjects` row vs. leave `project_subject_id` null. Resolving this
  unblocks either wiring the flag through `SessionStarter` (with a test) or
  removing the dead branch.
- **Dangling subject reference guard**  -  `ProjectSubjectResolver._require_subject`
  raises `SubjectResolutionError` if a referenced subject can't resolve. This
  is currently FK-guaranteed unreachable. If composite FK coverage is ever
  relaxed, add a focused test that forces the dangling state and asserts the
  error.
- **`project_subject_identities.create_user_identity` CHECK violation**  -  sets
  `verification_status='verified'` without `verified_at`, violating
  `ck_project_subject_identities_verified_at_consistent`. Zero production
  callers today. Fix (set `verified_at` or default to `unverified`) or delete
  when identity attachment is implemented.
- **Recognition-token issuance/rotation/expiry/revocation/cookie policy**  - 
  still missing (unchecked Phase 2.5 item).
- **`subject_ip_observations` retention/access policy**  -  still undecided.
- **Respondent identity-upgrade endpoints**  -  deliberately out of v1 scope
  unless product adds a UI for it.
- **`subject-access-doc-integration-checklist.md`**  -  delete once the Phase
  2.5 amendment is fully integrated and the checklist is no longer useful.
