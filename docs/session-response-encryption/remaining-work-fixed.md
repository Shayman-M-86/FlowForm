# Remaining Work — Session/Response Encryption

Consolidated view of what is still left after the schema, API contract, and
subject/access work.

This document is a target-local work queue. The policy source of truth remains:

- `core-policies.md`
- `Logical-flow-canonical.md`
- `flow-matrix.md`
- `api-structure.md`
- `session-flows.md`
- `answer-flows.md`
- `admin-and-operations.md`
- `cryptography.md`

---

## Current status

### Done

- Phase 1 schema work is done.
- Phase 2 public session API contract work is done.
- Admin response routes may exist as contract-only placeholders. Real admin
  read/export/delete behavior is still Phase 7 work.
- Phase 2.5 subject/access policy is done for v1:
  - access resolution and subject resolution are separate;
  - public slug and general link use open-access subject resolution;
  - private and authenticated links use assigned-access subject resolution;
  - authenticated links verify the logged-in identity but do not let it override
    the assigned subject;
  - single-use assigned links are consumed only with successful session start.

### Important corrected policy

Open-access sessions do create a canonical subject when no stronger context
exists.

For public slug and general-link access, subject authority is:

1. logged-in identity subject;
2. recognition-token subject;
3. new anonymous `ProjectSubject`.

For assigned links, the assigned subject always wins.

Recognition tokens are not consume-only. The implemented token action model is:

- `issue`
- `rotate`
- `mark_used`
- `keep`
- `none`

Tokens are for project-scoped subject continuity. They do not grant survey
access by themselves.

### Still not complete

The current core/access session-start path is not the full encrypted submission
system until it also provisions the response envelope and only exposes the
browser resume token after both required stores succeed.

What remains is:

- response-envelope creation during session start;
- cookie-backed current-session/resume handling;
- answer revision saves;
- question-view events;
- completion and lifecycle enforcement;
- real cryptography;
- admin reads/export/deletion behavior;
- frontend migration;
- verification and hardening.

---

## Phase 3 remainder — service skeleton without real crypto

### Repositories

- [ ] Core event repository.
- [ ] Response envelope repository.
- [ ] Response answer repository.
- [ ] Response revision repository.

Keep the repository rule: one repository should normally touch one database.
Cross-database coordination belongs in services.

### Services

- [ ] Session resumer/current-session service.
- [ ] Answer save service.
- [ ] Completion service.
- [ ] Admin response read service.
- [ ] Response export service.
- [ ] Response deletion service.
- [ ] Reconciliation service.

### Session start — remaining pieces

- [ ] Create a response envelope as part of session start.
- [ ] Derive or fake `session_locator` using the final locator-service
      interface.
- [ ] Generate or fake the envelope DEK using the final DEK-provider interface.
- [ ] Insert `response_envelopes` with the final column shape:
  - `session_locator`
  - `linkage_key_version`
  - `wrapped_dek`
  - `kms_key_arn`
  - `kms_context_version`
  - `crypto_version`
- [ ] Return/set the raw browser resume token only after the core session and
      response envelope both exist.
- [ ] If response-envelope creation fails after the core session was flushed,
      roll back or invalidate the unexposed core session.
- [ ] Do not consume a single-use link unless session start succeeds.
- [ ] Do not persist recognition-token or merge effects from a failed
      session-start attempt.

### Cookie-backed current-session guard

Create one shared loader used by `current`, answer save, question-viewed, and
complete commands.

- [ ] Read the `flowform_submission_session` cookie.
- [ ] Hash the raw browser resume token.
- [ ] Load the core session by `browser_session_token_hash`.
- [ ] Load the frozen survey version.
- [ ] Reject missing, expired, abandoned, or invalid sessions.
- [ ] Reject completed sessions for edit commands.
- [ ] Lock the session row for mutation commands.
- [ ] For `GET /current`, return safe respondent state with canonical latest
      answers.
- [ ] Never expose the core `session_id`, response envelope id, locators,
      wrapped DEK, KMS key data, ciphertext, or nonce values.

### Temporary crypto interfaces

Define the final method signatures and data shapes now. Use deterministic fake
locators and reversible placeholder ciphertext until Phase 6.

- [ ] Linkage secret provider.
- [ ] Locator service.
- [ ] DEK provider.
- [ ] Answer cipher.
- [ ] AAD builder.

The dev implementations must preserve the final service signatures so Phase 6
can replace internals without changing the session/answer services.

### Route placeholders to replace

- [ ] Replace the start-session placeholder, if still present, with the real
      session-start service.
- [ ] Replace the current-session placeholder with the session resumer.
- [ ] Replace the answer-save placeholder with the answer save service.
- [ ] Replace the question-viewed placeholder with the core event repository.
- [ ] Replace the complete placeholder with the completion service.

---

## Phase 4 — answer revision mechanics

### Answer validation

- [ ] Validate answers against the frozen survey version.
- [ ] Confirm the question-node UUID exists.
- [ ] Confirm the node is answerable.
- [ ] Confirm the `answer_family` matches the node.
- [ ] Validate the answer value against node constraints.
- [ ] Validate the question is valid within the current rule path where needed.
- [ ] Never trust frontend validation alone.

### First save

- [ ] Load and validate the current session.
- [ ] Derive or fake `session_locator`.
- [ ] Load the response envelope.
- [ ] Get the plaintext DEK from the dev/real DEK provider.
- [ ] Derive or fake `answer_locator`.
- [ ] Create the stable `response_answers` row.
- [ ] Create revision 1 in `response_answer_revisions`.
- [ ] Set `response_answers.latest_revision_id`.
- [ ] Commit the response transaction first.
- [ ] Insert the core `answer_saved` analytics event after the response write
      commits.
- [ ] Return success only after the authoritative response write succeeds.

### Changed answer

- [ ] Find the logical answer by `(envelope_id, answer_locator)`.
- [ ] Lock the logical-answer row.
- [ ] Read the current latest revision number.
- [ ] Insert the next immutable revision.
- [ ] Move `latest_revision_id` forward.
- [ ] Keep earlier ciphertext unchanged.

### Clear answer

- [ ] Treat clearing as a new encrypted revision.
- [ ] Do not delete `response_answers`.
- [ ] Do not delete earlier revisions.
- [ ] Store payload state as `cleared` with `answer = null`.

### Idempotency and concurrency

- [ ] Store `client_mutation_id` with each revision.
- [ ] Enforce idempotency using `(answer_id, client_mutation_id)`.
- [ ] Return the existing revision on retry with the same mutation ID.
- [ ] Handle simultaneous first saves using the `(envelope_id, answer_locator)`
      unique constraint.
- [ ] Handle simultaneous changed saves with row locks and sequential revision
      numbers.

---

## Phase 5 — completion and session lifecycle

### Question-viewed events

- [ ] Validate that `question_node_id` belongs to the frozen survey version.
- [ ] Insert a core `question_viewed` event.
- [ ] Treat this as secondary analytics metadata.
- [ ] If the analytics event fails, allow the respondent to continue.

### Completion

- [ ] Load and lock the current session.
- [ ] If already completed, return the existing completed state.
- [ ] Derive `session_locator`.
- [ ] Load the response envelope.
- [ ] Load canonical latest revisions.
- [ ] Decrypt or dev-decode the canonical answer set.
- [ ] Validate required questions, visible rule path, answer shapes, cleared
      answers, and completion requirements.
- [ ] Set `session_status = completed`.
- [ ] Set `completed_at`.
- [ ] Update `last_activity_at`.
- [ ] Insert a core `session_completed` event.
- [ ] Reject further respondent edits.

### Abandonment and expiry

- [ ] Reject writes to expired sessions.
- [ ] Add a maintenance path that marks stale in-progress sessions as
      `abandoned`.
- [ ] Keep the default behavior: abandoned sessions cannot be edited.
- [ ] Define project retention rules for partial responses before deleting
      abandoned response data.

---

## Phase 6 — real cryptography

Replace the dev crypto implementations with the real design in
`cryptography.md`.

- [ ] Secrets Manager-backed linkage-secret provider.
- [ ] Linkage-secret cache.
- [ ] HMAC-SHA-256 session locators.
- [ ] HMAC-SHA-256 answer locators.
- [ ] KMS `GenerateDataKey` DEK provider.
- [ ] KMS `Decrypt` path for reads.
- [ ] Short-lived in-memory DEK cache.
- [ ] Stable AAD construction.
- [ ] AES-256-GCM answer encryption/decryption.
- [ ] Fresh 12-byte nonce for every answer revision.
- [ ] Crypto-version dispatch.
- [ ] KMS-context-version dispatch.
- [ ] Old linkage-key versions remain readable.
- [ ] New sessions use the active linkage-key version.
- [ ] No plaintext answers, plaintext DEKs, raw linkage secrets, browser tokens,
      link tokens, or complete ciphertext/nonces in logs.

---

## Phase 7 — admin reads, export, and deletion

### Admin list

- [ ] List responses from core session metadata.
- [ ] Apply project/survey RBAC before returning rows.
- [ ] Do not touch encrypted answer payloads for a simple list unless needed.

### Admin detail

- [ ] Authorize project/survey response access.
- [ ] Load the core submission session.
- [ ] Derive `session_locator`.
- [ ] Load the response envelope.
- [ ] Load canonical latest revisions.
- [ ] Decrypt answer payloads.
- [ ] Validate decrypted question IDs against answer locators.
- [ ] Map question-node IDs to the frozen survey-version schema.
- [ ] Return the authorized response view.

### Admin history

- [ ] Add explicit history endpoint behavior.
- [ ] Load all revisions only when the history endpoint is requested.
- [ ] Keep the default detail view canonical-latest only.

### Export

- [ ] Use the same authorization and decrypt path as admin detail.
- [ ] Export canonical final answers by default.
- [ ] Add explicit historical export only if the product needs it.

### Delete

- [ ] Load the core session first.
- [ ] Derive `session_locator`.
- [ ] Delete the response envelope before deleting or anonymising the core
      session.
- [ ] Let response-database cascades remove answers and revisions.
- [ ] If one database succeeds and the other fails, mark deletion as pending
      and retry.
- [ ] Do not claim deletion completed until required stores are handled.

### Audit

- [ ] Add privileged-access audit logs.
- [ ] Record user id, project id, survey id, session id, action type,
      timestamp, and success/failure.
- [ ] Never store plaintext answers in audit logs.

---

## Phase 8 — frontend integration

### Public respondent site

- [ ] Move from one-shot submit to session start/resume.
- [ ] Save answers incrementally through
      `PUT /public/submission-sessions/current/answers/{question_node_id}`.
- [ ] Clear answers through the same answer route using `state = cleared`.
- [ ] Complete through `POST /public/submission-sessions/current/complete`.
- [ ] Handle missing, expired, completed, abandoned, and invalid session states.
- [ ] Stop sending browser-owned lifecycle fields such as session id,
      survey-version id, started timestamps, or completed timestamps.

### Studio

- [ ] Move results list/detail views to the new admin response routes.
- [ ] Add history view only behind explicit user action.
- [ ] Add export behavior through the new export route.
- [ ] Remove assumptions that a response is created only once at final submit.

### Legacy public routes

- [ ] Stop calling old one-shot routes:
  - `POST /api/v1/public/submissions/slug`
  - `POST /api/v1/public/submissions/link`
- [ ] Remove them or return `410 Gone` after the frontend migration window.

---

## Phase 9 — verification and hardening

### Tests

- [ ] Locator tests.
- [ ] Encryption tests.
- [ ] Session-start tests.
- [ ] Answer-revision tests.
- [ ] Idempotency tests.
- [ ] Completion tests.
- [ ] Rotation tests.
- [ ] Failure tests.

### Cross-database failure tests

- [ ] Core session write succeeds and response envelope creation fails.
- [ ] Response answer write succeeds and analytics event fails.
- [ ] KMS unavailable.
- [ ] Secrets Manager unavailable on cache miss.
- [ ] Response database unavailable.
- [ ] Core database unavailable.
- [ ] Lost HTTP response after successful save.
- [ ] Pending deletion retry.

### Reconciliation

- [ ] Core sessions without response envelopes.
- [ ] Stale session-initialization failures.
- [ ] Pending deletions.
- [ ] Inconsistent linkage-key versions.
- [ ] Missing response envelopes during admin reads.
- [ ] Analytics repair items where practical.

### Observability and privacy

- [ ] Metrics for session starts, answer saves, completions, abandonments,
      decrypt failures, KMS failures, response DB failures, core DB failures,
      and reconciliation repairs.
- [ ] Sanitize logs.
- [ ] Sanitize Sentry payloads.
- [ ] Sanitize tracing payloads.
- [ ] No plaintext answers, browser tokens, link tokens, plaintext DEKs, raw
      linkage secrets, complete ciphertext values, complete nonces, or auth
      cookies in logs.

### Operations

- [ ] IAM/KMS policy documentation.
- [ ] Key-rotation runbook.
- [ ] Linkage-secret rotation runbook.
- [ ] Response KEK rotation/re-wrap notes.
- [ ] Failure-alert rules.
- [ ] Deletion/reconciliation runbook.

---

## Closed or deferred policy items

### Closed for v1

- **Anonymous-subject creation:** closed. Public slug and general-link access
  create a new anonymous `ProjectSubject` when no logged-in identity or valid
  recognition token resolves a subject.
- **Assigned-link subject authority:** closed. Assigned subject always wins for
  private and authenticated assigned links.
- **Recognition-token lifecycle:** closed for session-start/account-linking
  behavior. `issue`, `rotate`, `mark_used`, `keep`, and `none` are part of the
  v1 token action model.
- **Recognition-token authority:** closed. Tokens support continuity only and
  do not grant access by themselves.

### Still deferred

- **Recognition-token management endpoints:** revocation endpoint,
  respondent-visible token refresh, explicit expiry policy, and any non-session
  issuance endpoint.
- **Dangling subject reference test:** only needed if composite FK coverage is
  relaxed. Keep the guard, but the state should remain unreachable under the
  current schema.
- **`subject_ip_observations`:** schema-only in v1. Do not write runtime
  observations until retention, access, abuse-prevention, and security review
  policy are defined.
- **Respondent identity-upgrade endpoints:** out of v1 unless the product adds
  a UI for voluntary identity upgrade.
