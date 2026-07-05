# Storage and Flows Reference

## Scope

This document is the verified reference for exact table shapes and the
respondent-facing flows that produce a core submission session. It
complements `01`-`06`, which describe the conceptual model — read this doc
when you need column lists, constraint names, service file paths, or to
check whether a table/column still exists.

It does not re-explain the locator/key concepts in `02-storage-and-locators.md`,
`03-session-envelope-lifecycle.md`, `04-answer-revisions.md`, or
`05-crypto-key-model.md`. Read those for the *why*; read this for the
*current, exact* shape.

Cross-checked against:

- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`
- `backend/app/schema/orm/`
- `backend/app/services/public_submissions/`
- `backend/app/api/v1/respondent/submission_sessions.py`

---

## 1. Core database: subject & identity model

### `project_subjects`

The pseudonymous, project-scoped participant record. Sessions, identities,
participants, and IP observations anchor to a `project_subjects` row, never
to a `users` row directly.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `subject_code` | TEXT | project-scoped pseudonymous participant code |
| `canonical_subject_id` | UUID | nullable, self-FK. Null = canonical row. Set = alias/merged subject pointing at its canonical subject. |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_project_subjects_project_id_id` — `UNIQUE (project_id, id)`.
- `uq_project_subjects_project_id_subject_code` — `UNIQUE (project_id, subject_code)`.
- `ck_project_subjects_subject_code_len` — trimmed, 1-128 chars.
- `ck_project_subjects_not_self_canonical` — `canonical_subject_id <> id`.
- `fk_project_subjects_canonical_subject` — `(project_id, canonical_subject_id)`
  -> `project_subjects(project_id, id)` ON DELETE RESTRICT.

Anonymous public/general-link sessions still create a new `project_subjects`
row when no other context resolves one — see the open-access subject
resolution path in Section 3.

The `canonical_subject_id` self-reference backs the subject-merge mechanic
used by `SubjectResolver` (Section 4): when a recognition token points at a
different subject than the one an assigned link/login resolves to, the
weaker subject is pointed at the stronger one via
`subjects.set_canonical_subject`, and canonical resolution is a one-hop
follow (no chains).

### `project_subject_identities`

Revocable identity attachments to a subject — either an email-based identity
or an attachment to an authenticated platform user.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | FK (composite, see below) |
| `identity_type` | TEXT | `'email'` \| `'authenticated_user'` |
| `user_id` | BIGINT | FK -> `users(id)` ON DELETE CASCADE; set only for `authenticated_user` |
| `normalized_email` | TEXT | see CHECK below |
| `verification_status` | TEXT | `'unverified'` \| `'verified'`, default `'unverified'` |
| `verified_at` | TIMESTAMPTZ | nullable |
| `attached_at` | TIMESTAMPTZ | default `NOW()` |
| `revoked_at` | TIMESTAMPTZ | nullable |

Constraints:

- `uq_project_subject_identities_project_subject_id` — `UNIQUE (project_id,
  project_subject_id, id)`. Lets `project_participants` prove (via FK) that
  a chosen identity belongs to a chosen subject within the same project.
- `fk_project_subject_identities_subject_same_project` — `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)` ON DELETE CASCADE.
- `fk_project_subject_identities_user_email_matches` — `(user_id,
  normalized_email)` -> `users(id, email)` ON DELETE CASCADE ON UPDATE
  CASCADE. Ties the identity's stored email to the platform user's current
  email — every `authenticated_user` identity carries (and must keep in
  sync with) the user's email.
- `ck_project_subject_identities_identity_type_valid` — `identity_type IN
  ('email', 'authenticated_user')`.
- `ck_project_subject_identities_identity_value_valid`:
  - `identity_type = 'email'` requires `normalized_email IS NOT NULL AND
    user_id IS NULL`.
  - `identity_type = 'authenticated_user'` requires `user_id IS NOT NULL
    AND normalized_email IS NOT NULL`.
- `ck_project_subject_identities_verification_status_valid` —
  `verification_status IN ('unverified', 'verified')`.
- `ck_project_subject_identities_verified_at_consistent` —
  `(verification_status = 'verified') = (verified_at IS NOT NULL)`.
- `ck_project_subject_identities_normalized_email_valid` — `normalized_email
  IS NULL OR (normalized_email = lower(btrim(normalized_email)) AND
  char_length(normalized_email) BETWEEN 3 AND 320)`.
- `ck_project_subject_identities_verified_at_after_attached_at`,
  `ck_project_subject_identities_revoked_at_after_attached_at` — ordering
  checks against `attached_at`.

Partial unique indexes:

- `uq_project_subject_identities_active_user` — one active authenticated
  subject per project: `UNIQUE (project_id, user_id) WHERE identity_type =
  'authenticated_user' AND user_id IS NOT NULL AND revoked_at IS NULL`.
- `uq_project_subject_identities_subject_active_email` — no duplicate active
  email on one subject.
- `uq_project_subject_identities_project_verified_email` — one verified
  active email owner per project.

### `project_participants`

Sits between `project_subjects`/`project_subject_identities` and
`survey_links`. Lets a `survey_links` row reach both a subject and a
specific identity (and, by extension, an email) through a single FK,
without storing an email directly on `survey_links`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | FK (composite, see below) |
| `identity_id` | UUID | FK (composite, see below) |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_project_participants_project_subject` — `UNIQUE (project_id,
  project_subject_id)`. One participant per subject per project.
- `uq_project_participants_project_id_id` — `UNIQUE (project_id, id)`. Lets
  `survey_links` target a participant within its project via composite FK.
- `fk_project_participants_subject_same_project` — `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)` ON DELETE
  CASCADE.
- `fk_project_participants_identity_same_subject` — `(project_id,
  project_subject_id, identity_id)` -> `project_subject_identities(project_id,
  project_subject_id, id)` ON DELETE CASCADE. Guarantees the participant's
  `identity_id` belongs to the participant's subject, within the same
  project.

A participant's "assigned email" is **derived** by joining
`project_participants.identity_id` -> `project_subject_identities.normalized_email`.
It is never stored on `project_participants` or `survey_links` directly.

### `project_subject_tokens`

Reusable subject-recognition tokens. Raw tokens are never stored — only a
SHA-256 hash.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | FK (composite) |
| `token_hash` | TEXT | unique, format `^[0-9a-f]{64}$` (SHA-256 hex) |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `last_used_at` | TIMESTAMPTZ | nullable |
| `revoked_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_project_subject_tokens_token_hash` — `UNIQUE (token_hash)`.
- `fk_project_subject_tokens_subject_same_project`.
- `ck_project_subject_tokens_token_hash_format` — `token_hash ~ '^[0-9a-f]{64}$'`.
- `ck_project_subject_tokens_expires_at_after_created_at`,
  `ck_project_subject_tokens_last_used_at_after_created_at`,
  `ck_project_subject_tokens_revoked_at_after_created_at`,
  `ck_project_subject_tokens_last_used_before_revocation` — ordering checks.

### `subject_ip_observations`

Append-only IP metadata, tied to a subject and/or a session. **Never copied
to the response database** — identity-bearing core metadata.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | nullable, FK -> `project_subjects(id)` ON DELETE CASCADE |
| `submission_session_id` | UUID | nullable, FK -> `submission_sessions(id)` ON DELETE CASCADE |
| `ip_address` | INET | NOT NULL |
| `observed_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `ck_subject_ip_observations_has_owner` — `project_subject_id IS NOT NULL
  OR submission_session_id IS NOT NULL`.
- `fk_subject_ip_observations_subject_same_project`,
  `fk_subject_ip_observations_session_same_project`,
  `fk_subject_ip_observations_session_subject_match` — consistency FKs.

---

## 2. Core database: sessions, encryption keys, events, and link assignment

### `linkage_key_versions`

Versioned metadata for the external linkage secret used to derive session
and answer locators (secret material itself lives outside Postgres — see
`05-crypto-key-model.md`).

| Column | Type | Notes |
|---|---|---|
| `version` | SMALLINT PK | |
| `aws_secret_id` | TEXT | NOT NULL |
| `aws_secret_version_id` | UUID | NOT NULL |
| `is_current` | BOOLEAN | default `FALSE` |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints: `ck_linkage_key_versions_version_valid` (`version > 0`),
`uq_linkage_key_versions_aws_secret_version`. A partial unique index
(`uq_linkage_key_versions_current`) enforces at most one `is_current = TRUE`
row.

### `survey_encryption_keys`

The KMS-wrapped survey branch key row — one per survey, created lazily at
publish time. See `05-crypto-key-model.md` for the key hierarchy.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | NOT NULL |
| `survey_id` | BIGINT | NOT NULL |
| `wrapped_survey_branch_key` | BYTEA | NOT NULL, non-empty |
| `kms_key_arn` | TEXT | NOT NULL, 1-2048 chars (trimmed) |
| `kms_context_version` | SMALLINT | NOT NULL, `> 0` |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints: `uq_survey_encryption_keys_survey`, `uq_survey_encryption_keys_project_survey`,
`fk_survey_encryption_keys_survey_same_project`, plus length/version CHECKs.

KMS metadata (`kms_key_arn`, `kms_context_version`) lives **only** on this
Core-DB row — the response envelope does not store it (see Section 3).

### `submission_sessions`

The anchor for a single respondent's run through a survey version.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `survey_id` | BIGINT | FK (composite, see below) |
| `survey_version_id` | BIGINT | FK (composite, see below) |
| `response_store_id` | BIGINT | FK -> `response_stores(id)` ON DELETE RESTRICT, also composite FK to same project |
| `link_id` | UUID | nullable, FK -> `survey_links(id)` ON DELETE SET NULL, also composite FK to same survey |
| `project_subject_id` | UUID | nullable, FK -> `project_subjects(id)` ON DELETE SET NULL, also composite FK to same project |
| `browser_session_token_hash` | BYTEA | NOT NULL, unique |
| `linkage_key_version` | SMALLINT | NOT NULL, FK -> `linkage_key_versions(version)` |
| `session_status` | TEXT | NOT NULL, default `'in_progress'` |
| `started_at` | TIMESTAMPTZ | default `NOW()` |
| `completed_at` | TIMESTAMPTZ | nullable |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `last_activity_at` | TIMESTAMPTZ | default `NOW()` |

Constraints (unchanged from earlier phase docs, still accurate):

- `uq_submission_sessions_browser_session_token_hash`, `uq_submission_sessions_id_survey_version_id`,
  `uq_submission_sessions_project_id_id`, `uq_submission_sessions_id_project_subject_id`.
- `ck_submission_sessions_session_status_valid` — `session_status IN
  ('in_progress', 'completed', 'abandoned')`.
- `ck_submission_sessions_completed_at_consistent`,
  `ck_submission_sessions_completed_at_after_started_at`,
  `ck_submission_sessions_expires_at_after_started_at`,
  `ck_submission_sessions_last_activity_at_after_started_at`,
  `ck_submission_sessions_completed_before_last_activity` — ordering rules.
- `fk_submission_sessions_survey_same_project`, `fk_submission_sessions_version_same_survey`
  (ON DELETE RESTRICT — a survey version cannot be deleted while sessions
  reference it), `fk_submission_sessions_store_same_project`,
  `fk_submission_sessions_link_same_survey`, `fk_submission_sessions_project_subject_same_project`.

Lifecycle: `in_progress` -> `completed` (sets `completed_at`) or
`in_progress` -> `abandoned` (no `completed_at`; reserved for a *committed*
session that can no longer be resumed — see `06-failure-and-logging-rules.md`
and `core/reconciliation.py`).

### `submission_answer_slots`

Tracks which questions a session has touched, scoped to the frozen survey
version. Used for membership validation (answer save / completion must
target a question that belongs to the session's frozen version) — not
present in earlier phase docs.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `submission_session_id` | UUID | NOT NULL, FK (composite, see below) |
| `survey_version_id` | BIGINT | NOT NULL |
| `question_node_id` | UUID | NOT NULL, FK (composite, see below) |
| `question_key` | TEXT | nullable |

Constraints:

- `uq_submission_answer_slots_session_question` — `UNIQUE
  (submission_session_id, question_node_id)`.
- `fk_submission_answer_slots_session_version` — `(submission_session_id,
  survey_version_id)` -> `submission_sessions(id, survey_version_id)` ON
  DELETE CASCADE.
- `fk_submission_answer_slots_question_same_version` — `(survey_version_id,
  question_node_id)` -> `survey_questions(survey_version_id, id)`.

### `submission_events`

Append-only event log per session.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `session_id` | UUID | FK (composite, see below) |
| `survey_version_id` | BIGINT | FK (composite, see below) |
| `event_type` | TEXT | NOT NULL |
| `question_node_id` | UUID | nullable, FK -> `survey_questions(id)` ON DELETE SET NULL, also composite FK to same version |
| `received_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `ck_submission_events_event_type_valid` — `event_type IN
  ('session_started', 'question_viewed', 'answer_saved', 'session_completed')`.
- `ck_submission_events_question_required_for_question_events`,
  `ck_submission_events_question_absent_for_session_events` — question
  presence gated by event type.
- `fk_submission_events_session_version`, `fk_submission_events_question_node_same_version`.

### `survey_links` — assignment-relevant columns

Full table also has `id`, `project_id`, `survey_id`, `name`, `token`,
`is_active`, `expires_at`, `used_at`, `emailed_at`, `created_at`. Note:
older docs described separate `token_prefix`/`token_hash` columns — the
current schema stores a single `token` column with `uq_survey_links_token`.

| Column | Type | Notes |
|---|---|---|
| `link_type` | TEXT | NOT NULL, default `'general'`. `'general' \| 'private' \| 'authenticated'` |
| `assignment_source` | TEXT | NOT NULL. `'manual' \| 'automated'` — always recorded regardless of `link_type` |
| `assigned_participant_id` | UUID | nullable, FK -> `project_participants(project_id, id)` ON DELETE RESTRICT |

Semantics of `link_type`:

- `general` — anonymous; anyone with the URL; no assigned participant.
- `private` — no sign-in required; possession of the bearer token is the
  proof of identity; must be assigned to a participant.
- `authenticated` — Auth0 sign-in required; must be assigned to a participant.

Constraints (assignment-related):

- `fk_survey_links_assigned_participant_same_project` — `(project_id,
  assigned_participant_id)` -> `project_participants(project_id, id)` ON
  DELETE RESTRICT. RESTRICT is intentional: deleting a participant must not
  silently demote an assigned link to general.
- `ck_survey_links_link_type_valid`, `ck_survey_links_assignment_source_valid`.
- `ck_survey_links_general_has_no_assignment` — `link_type <> 'general' OR
  assigned_participant_id IS NULL`.
- `ck_survey_links_assigned_requires_participant` — `link_type = 'general'
  OR assigned_participant_id IS NOT NULL`.
- `ck_survey_links_used_at_requires_assignment` — `used_at IS NULL OR
  assigned_participant_id IS NOT NULL`. Single-use semantics are derived
  from carrying a participant assignment.

---

## 3. Response database: encrypted answer model

The response database stores only anonymous, encrypted payload data. It has
no FK relationship to the core database — see `02-storage-and-locators.md`.

**Two tables, no revision history.** Each answer save overwrites the
current row for its `answer_locator` (`ON CONFLICT DO UPDATE`) rather than
appending a new immutable revision. See `04-answer-revisions.md` for the
save semantics.

### `response_envelopes`

One envelope per submission session — the encrypted counterpart to a
`submission_sessions` row, linked only via `session_locator`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `session_locator` | BYTEA | NOT NULL, unique, exactly 32 bytes |
| `linkage_key_version` | SMALLINT | NOT NULL, `> 0` |
| `wrapped_session_dek` | BYTEA | NOT NULL, non-empty. Wrapped **locally** by the survey branch key, not directly by KMS. |
| `crypto_version` | SMALLINT | NOT NULL, `> 0` |

Constraints:

- `uq_response_envelopes_session_locator`, `ck_response_envelopes_session_locator_len`
  (`= 32` bytes), `ck_response_envelopes_linkage_key_version_valid`,
  `ck_response_envelopes_wrapped_session_dek_len`, `ck_response_envelopes_crypto_version_valid`.

No `kms_key_arn` / `kms_context_version` columns here — that metadata lives
on Core's `survey_encryption_keys` row (Section 2). The Response DB never
sees KMS metadata.

### `response_answers`

**Single mutable row per answer locator** — not an append-only revision
chain. `PRIMARY KEY (answer_locator)`.

| Column | Type | Notes |
|---|---|---|
| `answer_locator` | BYTEA PK | opaque HMAC-derived lookup, exactly 32 bytes |
| `envelope_id` | UUID | NOT NULL, FK -> `response_envelopes(id)` ON DELETE CASCADE |
| `ciphertext` | BYTEA | NOT NULL, non-empty — encrypted payload containing the real question-node UUID, answer state, and answer value |
| `nonce` | BYTEA | NOT NULL, exactly 12 bytes — fresh per write |
| `client_mutation_id` | UUID | nullable — idempotency key for the save request that produced the current row |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `NOW()` |

Constraints:

- `ck_response_answers_answer_locator_len` (`= 32`), `ck_response_answers_nonce_len`
  (`= 12`), `ck_response_answers_ciphertext_non_empty`.
- `fk_response_answers_envelope_id__response_envelopes` — ON DELETE CASCADE.
- `uq_response_answers_envelope_id_nonce` — prevents nonce reuse within an
  envelope (AES-GCM safety) across writes.

Index: `idx_response_answers_envelope` on `envelope_id`.

Write path: `upsert_current()` in
`backend/app/repositories/response/response_answer_repo.py` — an `INSERT
... ON CONFLICT (answer_locator) DO UPDATE` that overwrites `envelope_id`,
`ciphertext`, `nonce`, `client_mutation_id`, `updated_at`. There is no
`response_answer_revisions` table and no revision-number column.

---

## 4. Core/response linkage

There are **no foreign keys between the core and response databases** —
they are physically separate Postgres databases. The link is a
cryptographic one, derived at request time from `submission_sessions.id`
and `submission_sessions.linkage_key_version`. See `02-storage-and-locators.md`
for the full locator model and `05-crypto-key-model.md` for the key
hierarchy that protects the wrapped material stored in `response_envelopes`.

---

## 5. Respondent-facing flows

### Service class map

| Concern | Class | File |
|---|---|---|
| Session lifecycle (start/answer/event/complete) | `SessionManagementService` | `services/public_submissions/api/session_management.py` |
| Survey browsing, link resolution, account linking | `SurveyResolveService` | `services/public_submissions/api/survey_resolve.py` |
| Access grant from slug or link token | `AccessResolver` | `services/public_submissions/core/resolution/access_resolver.py` |
| Subject priority waterfall + merge/token instructions | `SubjectResolver` | `services/public_submissions/core/resolution/subject_resolver.py` |
| Recognition token lifecycle | `SubjectTokenService` | `services/public_submissions/core/resolution/subject_token.py` |
| Session-subject write orchestration | — | `services/public_submissions/core/resolution/session_subject_service.py` |
| Session-start orchestration | — | `services/public_submissions/core/actions/session_starter.py` |
| Answer save | — | `services/public_submissions/core/actions/answer_save.py` |
| Completion | — | `services/public_submissions/core/actions/completion.py` |
| Current-session loading | — | `services/public_submissions/core/session_loader.py` |
| Orphan/abandoned session reconciliation | — | `services/public_submissions/core/reconciliation.py` |

### Link resolution flow

`POST /links/resolve` -> `SurveyResolveService.resolve_link` ->
`AccessResolver.resolve_link_token` ->
`submission_access_rules.ensure_link_token_access` (`backend/app/domain/submission_access_rules.py`).

`ensure_link_token_access` performs, in order:

- `public_link_rules.ensure_is_active`
- `public_link_rules.ensure_not_expired`
- `public_link_rules.ensure_auth_satisfied`
- `public_link_rules.ensure_not_used`
- `public_link_rules.ensure_link_allowed_by_survey_visibility` — a general
  (unassigned) link on a `visibility="private"` survey raises
  `PrivateSurveyAssignedEmailRequiredError`.

If `actor is None` or `link.link_type != "authenticated"`, resolution
returns here — no participant checks apply.

For an **authenticated link** accessed by a **logged-in actor**:

- Missing `assigned_participant_id` -> `LinkAuthAssignmentRequiredError`
  (422, `LINK_ASSIGNED_PARTICIPANT_REQUIRED`).
- `ensure_participant_identity_authenticated` — non-authenticated identity
  -> `LinkParticipantVerificationRequiredError` (403,
  `LINK_PARTICIPANT_VERIFICATION_REQUIRED`).
- `ensure_actor_matches_participant_identity` — identity's `user_id` !=
  actor's id -> `LinkAssignmentMismatchError` (403,
  `LINK_ASSIGNED_TO_ANOTHER_USER`).

`ensure_link_token_access` is the **same function** called during session
start (`POST /submission-sessions`), so an authenticated link that isn't
usable via `/links/resolve` is rejected at session start with the same
error codes.

`POST /links/verification/link` -> `SurveyResolveService.verify_authenticated_link_participant`
-> `ParticipantService.verify_participant_for_user` is the separate flow
that *creates* the authenticated-user identity link (email-match rule
between actor and the participant's stored email), then reconciles the
recognition token via `SubjectResolver.resolve_assigned_subject` and
`SubjectTokenService.apply_token_action`.

### Subject resolution flow

`SubjectResolver.resolve` routes to one of two paths based on
`access_method`, returning a `SubjectResolutionResult` with
`final_subject_id`, `subject_source`, `token_action`, and optional merge
instructions. The caller applies all writes before committing.

Recognition-token lookup happens first and is read-only:
`SubjectTokenService.lookup` resolves the raw token to `token_subject_id` /
`canonical_token_subject_id` without stamping `last_used_at`.

**Assigned-access path** (private link, authenticated link): the assigned
subject always wins; the token is used only for continuity cleanup
(`keep`/`rotate`/merge into the assigned canonical subject).

**Open-access path** (public slug, general link): priority waterfall —
logged-in identity > recognition token > new anonymous subject. Anonymous
open-access sessions always get a new `project_subjects` row when no other
context resolves one — `submission_sessions.project_subject_id` is never
`NULL` for open-access sessions.

### Session start flow

`POST /submission-sessions` -> `SessionManagementService.start_session` ->
`session_starter.start` (`backend/app/services/public_submissions/core/actions/session_starter.py`):

1. `AccessResolver.resolve` resolves a `public_slug` or link `token` into a
   `SubmissionAccessGrant`.
2. `survey_rules.ensure_has_response_store` confirms a linked response store.
3. Read-only recognition-token lookup via `SubjectTokenService.lookup`.
4. `SubjectResolver.resolve` returns the subject resolution result.
5. Apply canonical merge (if instructed), apply identity write (if
   instructed), apply token action (`issue`/`rotate`/`mark_used`/`keep`/`none`).
6. Generate the browser session token, insert the `submission_sessions` row
   (frozen `survey_version_id`, `link_id` if used, `final_subject_id`,
   hashed browser token, `response_store_id`).
7. **Create the encrypted response envelope** — derive the session locator,
   unwrap the survey branch key, generate and locally wrap a fresh session
   DEK, insert the `response_envelopes` row. This step is fully implemented;
   see `03-session-envelope-lifecycle.md` Section 1 for the exact crypto
   sequence and `06-failure-and-logging-rules.md` for the partial-failure
   handling between this step and the core commit.
8. Mark single-use links used, commit, return `(session_response,
   raw_browser_session_token, raw_recognition_token)`. The route sets
   cookies and returns `201`.

`survey_schema` is set to `published_version.compiled_schema` for
**public-slug** access; it is `None` for link-based access (schema was
delivered at link-resolve time).

### Implemented routes

All routes live in `backend/app/api/v1/respondent/submission_sessions.py`
and are fully wired (no stubs/placeholders remain):

| Route | Handler | Behavior doc |
|---|---|---|
| `POST /submission-sessions` | `start_submission_session` | `03-session-envelope-lifecycle.md` §1 |
| `PUT /submission-sessions/current/answers/<question_node_id>` | `save_submission_session_answer` | `03-session-envelope-lifecycle.md` §3, `04-answer-revisions.md` |
| `POST /submission-sessions/current/events` | `record_submission_session_event` | `03-session-envelope-lifecycle.md` §4 |
| `POST /submission-sessions/current/complete` | `complete_submission_session` | `03-session-envelope-lifecycle.md` §5 |

There is no public current-session read route by design — cookie-backed
session lookup (`session_loader.py`) is an internal guard used by the
command routes above, not a respondent data-rehydration endpoint.

---

## Sources

- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`
- `backend/app/schema/orm/`
- `backend/app/repositories/response/response_answer_repo.py`
- `backend/app/services/public_submissions/`
- `backend/app/api/v1/respondent/submission_sessions.py`
- `backend/app/domain/submission_access_rules.py`
