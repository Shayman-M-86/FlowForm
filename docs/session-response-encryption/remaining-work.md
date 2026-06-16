# Remaining Work  -  Session/Response Encryption

Consolidated view of what's left, derived from the prior implementation
checklist Phase 3 onward, the `TODO(phase*)` markers in
`app/api/v1/public.py`, and the session-service open-issues audit.

## Status summary

Phase 1 (schema) is done. Phase 2 (API contracts  -  public and admin route
stubs) is done. Phase 2.5 (subject access model) is done for the conservative
v1 policy:
`SessionStarter`, `ProjectSubjectResolver`, and `SurveyAccessResolver` are
real, integration-tested services. The session-start service is real  -  it
resolves access (public slug or link token), resolves the optional subject
from server-owned context, binds one survey version, and generates/hashes a
browser session token. Anonymous public/general-link sessions do not create
`project_subjects` rows by default, recognition tokens are consume-only, and
`subject_ip_observations` remains schema-only until retention/access policy is
expanded. What remains is everything downstream of session start: response
envelopes, resume, answer revisions, completion, real cryptography, admin
reads, frontend integration, and hardening.

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

**Cookie-backed session guard**
- [ ] Hash the browser token
- [ ] Load an in-progress session
- [ ] Reject expired, completed, or abandoned sessions
- [ ] Use this lookup internally for answer/event/complete commands; do not
      expose in-process answer hydration through a public read endpoint

**Temporary crypto interfaces (dev implementations)**

Define final method signatures/shapes now, backed by deterministic fake
locators and reversible placeholder ciphertext until Phase 6:
- [ ] Linkage secret provider
- [ ] Locator service
- [ ] DEK provider
- [ ] Answer cipher
- [ ] AAD builder

**`public.py` placeholders to replace**
- [ ] `public.py:185` `TODO(phase3)`  -  question-viewed event route is a
      placeholder; needs real persistence via the core event repository

## Phase 4-5

### Phase 4  -  answer revision mechanics
- [ ] Validate answers against the frozen survey version
      (`public.py:161` `TODO(phase4)`)
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
- [ ] Completion (`public.py:200` `TODO(phase5)`): validate required
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

## Deferred policy items

From the session-service open-issues audit:

- **Anonymous-subject-creation policy**  -  for open-access flows (public slug,
  general link) `SubjectResolver` always creates a new `project_subjects` row
  when no other context resolves a subject, so `project_subject_id` is never
  `NULL` for open-access sessions. For assigned-access flows (private,
  authenticated link) the assigned subject is always used. There is no
  `create_anonymous_subject=False` escape hatch in the current code.
- **Dangling subject reference guard**  -  `SubjectResolver._require_subject`
  raises `SubjectResolutionError` if a referenced subject can't resolve. This
  is currently FK-guaranteed unreachable. If composite FK coverage is ever
  relaxed, add a focused test that forces the dangling state and asserts the
  error.
- **Recognition-token full lifecycle**  -  issue, rotate, mark_used, keep, and
  none actions are all implemented in `SubjectTokenService` and wired into
  session start and account-linking flows. Remaining deferred items: revocation
  endpoints, cookie-expiry policy, and explicit issuance endpoints accessible
  to respondents outside of session start.
- **`subject_ip_observations` retention/access policy**  -  schema-only in v1.
  Do not write runtime observations until retention, access, and abuse/security
  use cases are explicitly defined.
- **Respondent identity-upgrade endpoints**  -  deliberately out of v1 scope
  unless product adds a UI for it.
