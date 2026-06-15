# Data Model  -  Session/Response Encryption (Phase 1)

## Scope

This document is the consolidated, verified data-model reference for the
session/response encryption work. It describes the **current** shape of the
core-database subject/identity/participant model, the session and
event-tracking tables, the `survey_links` assignment model, and the
response-database encrypted envelope model  -  as they exist in
`infra/postgres/init/schema/flowform_core_db_schema_v4.sql` and
`infra/postgres/init/schema/flowform_response_db_schema_v4.sql`, cross-checked
against the ORM models in `backend/app/schema/orm/core/`.

It does not duplicate the architecture or respondent-flow narratives in
[architecture.md](architecture.md) or [flows.md](flows.md). Read this doc when
you need exact column lists, constraint names, or to check whether a
table/column still exists.

Earlier phase docs described a pre-Phase-1 or early-Phase-1 shape. Where this
doc conflicts with those older notes, **this doc and the SQL/ORM files are
the ground truth**. The discrepancies found are called out explicitly below.

---

## 1. Core database: subject & identity model

### `project_subjects`

The pseudonymous, project-scoped participant record. Every respondent
interaction (sessions, identities, participants, IP observations) is anchored
to a `project_subjects` row, never to a `users` row directly.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `subject_code` | TEXT | project-scoped pseudonymous participant code |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_project_subjects_project_id_id` - `UNIQUE (project_id, id)`. Lets
  composite FKs prove a subject belongs to the same project.
- `uq_project_subjects_project_id_subject_code` - `UNIQUE (project_id,
  subject_code)`. Keeps participant codes unique within a project.
- `ck_project_subjects_subject_code_len` - `subject_code = btrim(subject_code)`
  and `char_length(subject_code) BETWEEN 1 AND 128`.

### `project_subject_identities`

Revocable identity attachments to a subject  -  either an email-based identity
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

- `uq_project_subject_identities_project_subject_id`  - 
  **`UNIQUE (project_id, project_subject_id, id)`**. This is a composite
  uniqueness, not a simple per-subject uniqueness  -  it exists so
  `project_participants` can prove (via FK) that a chosen identity belongs to
  a chosen subject within the same project.
- `fk_project_subject_identities_subject_same_project`  -  `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)` ON DELETE
  CASCADE.
- `fk_project_subject_identities_user_email_matches`  -  **new FK**: `(user_id,
  normalized_email)` -> `users(id, email)` ON DELETE CASCADE ON UPDATE
  CASCADE. This ties the identity's stored email to the platform user's
  current email.
- `ck_project_subject_identities_identity_type_valid`  - 
  `identity_type IN ('email', 'authenticated_user')`.
- `ck_project_subject_identities_identity_value_valid`  -  **(corrected, see
  discrepancy below)**:
  - `identity_type = 'email'` requires `normalized_email IS NOT NULL AND
    user_id IS NULL`.
  - `identity_type = 'authenticated_user'` requires `user_id IS NOT NULL
    AND normalized_email IS NOT NULL`.
- `ck_project_subject_identities_verification_status_valid`  - 
  `verification_status IN ('unverified', 'verified')`.
- `ck_project_subject_identities_verified_at_consistent`  - 
  `(verification_status = 'verified') = (verified_at IS NOT NULL)`.
- `ck_project_subject_identities_normalized_email_valid`  -  `normalized_email
  IS NULL OR (normalized_email = lower(btrim(normalized_email)) AND
  char_length(normalized_email) BETWEEN 3 AND 320)`.
- `ck_project_subject_identities_verified_at_after_attached_at`  - 
  `verified_at IS NULL OR verified_at >= attached_at`.
- `ck_project_subject_identities_revoked_at_after_attached_at`  - 
  `revoked_at IS NULL OR revoked_at >= attached_at`.

Partial unique indexes:

- `uq_project_subject_identities_active_user`  -  one active authenticated
  subject per project: `UNIQUE (project_id, user_id) WHERE identity_type =
  'authenticated_user' AND user_id IS NOT NULL AND revoked_at IS NULL`.
- `uq_project_subject_identities_subject_active_email`  -  no duplicate active
  email on one subject: `UNIQUE (project_subject_id, normalized_email) WHERE
  identity_type = 'email' AND normalized_email IS NOT NULL AND revoked_at IS
  NULL`.
- `uq_project_subject_identities_project_verified_email`  -  one verified
  active email owner per project: `UNIQUE (project_id, normalized_email)
  WHERE identity_type = 'email' AND normalized_email IS NOT NULL AND
  verification_status = 'verified' AND revoked_at IS NULL`.

> **Discrepancy from older docs**: older docs (including the prior version of
> `core-database-schema.md`) describe
> `ck_project_subject_identities_identity_value_valid` as requiring
> `authenticated_user` rows to have `normalized_email IS NULL`. The **current**
> constraint requires `normalized_email IS NOT NULL` for `authenticated_user`
> rows too, and adds `fk_project_subject_identities_user_email_matches` tying
> that email to `users.email`. This is a real behavior change from what the
> older docs describe  -  every `authenticated_user` identity now carries (and
> must keep in sync with) the user's email.

### `project_participants` (new table)

**Not present in older docs.** Sits between
`project_subjects`/`project_subject_identities` and `survey_links`. It exists
so a `survey_links` row can reach both a subject and a specific identity
(and, by extension, an email) through a single FK, without storing an email
directly on `survey_links`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | FK (composite, see below) |
| `identity_id` | UUID | FK (composite, see below) |
| `created_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_project_participants_project_subject`  -  `UNIQUE (project_id,
  project_subject_id)`. One participant per subject per project.
- `uq_project_participants_project_id_id`  -  `UNIQUE (project_id, id)`. Lets
  `survey_links` target a participant within its project via a same-project
  composite FK.
- `fk_project_participants_subject_same_project`  -  `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)` ON DELETE
  CASCADE.
- `fk_project_participants_identity_same_subject`  -  `(project_id,
  project_subject_id, identity_id)` -> `project_subject_identities(project_id,
  project_subject_id, id)` ON DELETE CASCADE. This is the guarantee that the
  participant's `identity_id` actually belongs to the participant's subject,
  within the same project  -  it is what lets a link resolve both subject and
  identity/email through `project_participants` alone.

A participant's "assigned email" (used when rendering link assignment info)
is **derived** by joining `project_participants.identity_id` ->
`project_subject_identities.normalized_email`. It is never stored on
`project_participants` or `survey_links` directly.

### `project_subject_tokens`

Reusable subject-recognition tokens. Raw tokens are never stored  -  only a
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

- `uq_project_subject_tokens_token_hash`  -  `UNIQUE (token_hash)`.
- `fk_project_subject_tokens_subject_same_project`  -  `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)` ON DELETE
  CASCADE.
- `ck_project_subject_tokens_token_hash_format`  -  `token_hash ~
  '^[0-9a-f]{64}$'`.
- `ck_project_subject_tokens_expires_at_after_created_at`  -  `expires_at >
  created_at`.
- `ck_project_subject_tokens_last_used_at_after_created_at`  - 
  `last_used_at IS NULL OR last_used_at >= created_at`.
- `ck_project_subject_tokens_revoked_at_after_created_at`  -  `revoked_at IS
  NULL OR revoked_at >= created_at`.
- `ck_project_subject_tokens_last_used_before_revocation`  -  `revoked_at IS
  NULL OR last_used_at IS NULL OR last_used_at <= revoked_at`.

### `subject_ip_observations`

Append-only IP metadata, tied to a subject and/or a session. **Never copied
to the response database**  -  this is identity-bearing core metadata.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `project_id` | BIGINT | FK -> `projects(id)` ON DELETE CASCADE |
| `project_subject_id` | UUID | nullable, FK -> `project_subjects(id)` ON DELETE CASCADE |
| `submission_session_id` | UUID | nullable, FK -> `submission_sessions(id)` ON DELETE CASCADE |
| `ip_address` | INET | NOT NULL |
| `observed_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `ck_subject_ip_observations_has_owner`  -  `project_subject_id IS NOT NULL OR
  submission_session_id IS NOT NULL`. At least one owner must be set.
- `fk_subject_ip_observations_subject_same_project`  -  `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)`.
- `fk_subject_ip_observations_session_same_project`  -  `(project_id,
  submission_session_id)` -> `submission_sessions(project_id, id)`.
- `fk_subject_ip_observations_session_subject_match`  - 
  `(submission_session_id, project_subject_id)` ->
  `submission_sessions(id, project_subject_id)`. If both owner columns are
  set, they must refer to a consistent subject/session pair.

---

## 2. Core database: sessions, events, and link assignment

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
| `linkage_key_version` | SMALLINT | NOT NULL, default `1` |
| `session_status` | TEXT | NOT NULL, default `'in_progress'` |
| `started_at` | TIMESTAMPTZ | default `NOW()` |
| `completed_at` | TIMESTAMPTZ | nullable |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `last_activity_at` | TIMESTAMPTZ | default `NOW()` |

Constraints:

- `uq_submission_sessions_browser_session_token_hash`  -  `UNIQUE
  (browser_session_token_hash)`. Each browser-session token hash identifies
  at most one session.
- `uq_submission_sessions_id_survey_version_id`  -  `UNIQUE (id,
  survey_version_id)`. Lets `submission_events` target a session+version
  combination via composite FK.
- `uq_submission_sessions_project_id_id`  -  `UNIQUE (project_id, id)`.
- `uq_submission_sessions_id_project_subject_id`  -  `UNIQUE (id,
  project_subject_id)`. Lets `subject_ip_observations` verify
  session/subject consistency.
- `ck_submission_sessions_browser_session_token_hash_len`  - 
  `length(browser_session_token_hash) >= 32`.
- `ck_submission_sessions_linkage_key_version_valid`  - 
  `linkage_key_version > 0`.
- `ck_submission_sessions_session_status_valid`  -  `session_status IN
  ('in_progress', 'completed', 'abandoned')`.
- `ck_submission_sessions_completed_at_consistent`  -  `(session_status =
  'completed') = (completed_at IS NOT NULL)`. A session is `completed` iff
  `completed_at` is set.
- `ck_submission_sessions_completed_at_after_started_at`  -  `completed_at IS
  NULL OR completed_at >= started_at`.
- `ck_submission_sessions_expires_at_after_started_at`  -  `expires_at >
  started_at`.
- `ck_submission_sessions_last_activity_at_after_started_at`  - 
  `last_activity_at >= started_at`.
- `ck_submission_sessions_completed_before_last_activity`  -  `completed_at IS
  NULL OR completed_at <= last_activity_at`.
- `fk_submission_sessions_survey_same_project`  -  `(project_id, survey_id)` ->
  `surveys(project_id, id)` ON DELETE CASCADE.
- `fk_submission_sessions_version_same_survey`  -  `(survey_id,
  survey_version_id)` -> `survey_versions(survey_id, id)` ON DELETE RESTRICT.
- `fk_submission_sessions_store_same_project`  -  `(project_id,
  response_store_id)` -> `response_stores(project_id, id)`.
- `fk_submission_sessions_link_same_survey`  -  `(survey_id, link_id)` ->
  `survey_links(survey_id, id)`.
- `fk_submission_sessions_project_subject_same_project`  -  `(project_id,
  project_subject_id)` -> `project_subjects(project_id, id)`.

`session_status` lifecycle: `in_progress` -> `completed` (sets
`completed_at`, must be `<= last_activity_at` and `>= started_at`) or
`in_progress` -> `abandoned` (no `completed_at`).

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

- `ck_submission_events_event_type_valid`  -  `event_type IN
  ('session_started', 'question_viewed', 'answer_saved',
  'session_completed')`.
- `ck_submission_events_question_required_for_question_events`  - 
  `event_type NOT IN ('question_viewed', 'answer_saved') OR question_node_id
  IS NOT NULL`. `question_viewed`/`answer_saved` events must reference a
  question.
- `ck_submission_events_question_absent_for_session_events`  -  `event_type NOT
  IN ('session_started', 'session_completed') OR question_node_id IS NULL`.
  Session-level events must not reference a question.
- `fk_submission_events_session_version`  -  `(session_id, survey_version_id)`
  -> `submission_sessions(id, survey_version_id)` ON DELETE CASCADE.
- `fk_submission_events_question_node_same_version`  -  `(survey_version_id,
  question_node_id)` -> `survey_questions(survey_version_id, id)`.

### `survey_links`  -  assignment-relevant columns

`survey_links` predates this phase, but its assignment model changed
substantially. Full table also has `id`, `project_id`, `survey_id`, `name`,
`token_prefix`, `token_hash`, `is_active`, `expires_at`, `used_at`,
`created_at` (unchanged from prior docs). The assignment-relevant columns:

| Column | Type | Notes |
|---|---|---|
| `link_type` | TEXT | NOT NULL, default `'general'`. `'general' \| 'private' \| 'authenticated'`  -  **new column** |
| `assignment_source` | TEXT | NOT NULL. `'manual' \| 'automated'`  -  always recorded regardless of `link_type` |
| `assigned_participant_id` | UUID | nullable, FK -> `project_participants(project_id, id)` ON DELETE RESTRICT  -  **replaces `assigned_subject_id`** |

Semantics of `link_type`:

- `general`  -  anonymous; anyone with the URL; no assigned participant.
- `private`  -  no sign-in required; possession of the bearer token is the
  proof of identity; must be assigned to a participant.
- `authenticated`  -  Auth0 sign-in required; must be assigned to a
  participant.

Constraints (assignment-related):

- `fk_survey_links_assigned_participant_same_project`  -  `(project_id,
  assigned_participant_id)` -> `project_participants(project_id, id)` ON
  DELETE RESTRICT. RESTRICT is intentional: deleting a participant must not
  silently demote an assigned link to general.
- `ck_survey_links_link_type_valid`  -  `link_type IN ('general', 'private',
  'authenticated')`.
- `ck_survey_links_assignment_source_valid`  -  `assignment_source IN
  ('manual', 'automated')`.
- `ck_survey_links_general_has_no_assignment`  -  `link_type <> 'general' OR
  assigned_participant_id IS NULL`. A general link carries no assigned
  participant.
- `ck_survey_links_assigned_requires_participant`  -  `link_type = 'general' OR
  assigned_participant_id IS NOT NULL`. Private and authenticated links must
  be assigned.
- `ck_survey_links_used_at_requires_assignment`  -  `used_at IS NULL OR
  assigned_participant_id IS NOT NULL`. Single-use semantics are derived from
  carrying a participant assignment.

> **Discrepancy from older docs**: older docs (including
> `core-database-schema.md`) describe `survey_links.assigned_subject_id` ->
> `project_subjects.id` and a separate `assigned_email` column, with
> constraints keyed on `assigned_email OR assigned_subject_id`. **Both of
> those columns are gone.** The current model has a single
> `assigned_participant_id` -> `project_participants(project_id, id)`, plus
> the new `link_type` column (which did not exist at all in the old schema
> docs). The assigned email is now derived by joining
> `survey_links.assigned_participant_id` -> `project_participants.identity_id`
> -> `project_subject_identities.normalized_email`; it is not stored on
> `survey_links`.

---

## 3. Response database: encrypted envelope model

The response database stores only anonymous, encrypted payload data. It has
no FK relationship to the core database (see [Section 4](#4-coreresponse-linkage)).

> **Implementation status**: the column shapes below are the final Phase-1
> schema and are enforced by the constraints listed. However, real KMS/local
> cryptography is **Phase 6, not yet implemented**. As of Phase 1,
> `wrapped_dek`, `ciphertext`, `nonce`, `session_locator`, and `answer_locator`
> are structurally enforced (lengths, formats, uniqueness) but are not yet
> populated by production crypto flows  -  Phases 2-5 (API routes, service
> orchestration, answer revision mechanics, lifecycle behavior) are also open.

### `response_envelopes`

One envelope per submission session  -  the encrypted counterpart to a
`submission_sessions` row, linked only via `session_locator` (see Section 4).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `session_locator` | BYTEA | NOT NULL, unique, exactly 32 bytes |
| `linkage_key_version` | SMALLINT | NOT NULL, `> 0` |
| `wrapped_dek` | BYTEA | NOT NULL, non-empty |
| `kms_key_arn` | TEXT | NOT NULL, 1-2048 chars (trimmed) |
| `kms_context_version` | SMALLINT | NOT NULL, `> 0` |
| `crypto_version` | SMALLINT | NOT NULL, `> 0` |

Constraints:

- `uq_response_envelopes_session_locator`  -  `UNIQUE (session_locator)`.
- `ck_response_envelopes_session_locator_len`  -  `octet_length(session_locator)
  = 32`.
- `ck_response_envelopes_linkage_key_version_valid`  - 
  `linkage_key_version > 0`.
- `ck_response_envelopes_wrapped_dek_len`  -  `octet_length(wrapped_dek) > 0`.
- `ck_response_envelopes_kms_key_arn_len`  - 
  `char_length(btrim(kms_key_arn)) BETWEEN 1 AND 2048`.
- `ck_response_envelopes_crypto_version_valid`  -  `crypto_version > 0`.
- `ck_response_envelopes_kms_context_version_valid`  - 
  `kms_context_version > 0`.

### `response_answers`

One row per answered question within an envelope. Tracks the current
("latest") revision pointer.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `envelope_id` | UUID | NOT NULL, FK -> `response_envelopes(id)` ON DELETE CASCADE |
| `answer_locator` | BYTEA | NOT NULL, exactly 32 bytes |
| `latest_revision_id` | UUID | NOT NULL |

Constraints:

- `ck_response_answers_answer_locator_len`  -  `octet_length(answer_locator) =
  32`.
- `uq_response_answers_id_envelope_id`  -  `UNIQUE (id, envelope_id)`. Lets
  `response_answer_revisions` target an answer+envelope pair via composite
  FK.
- `uq_response_answers_envelope_id_answer_locator`  -  `UNIQUE (envelope_id,
  answer_locator)`. An answer locator is unique within its envelope.

### `response_answer_revisions`

Append-only revision history for an answer's encrypted content.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | default `gen_random_uuid()` |
| `answer_id` | UUID | NOT NULL, FK (composite, see below) |
| `envelope_id` | UUID | NOT NULL, part of composite FK |
| `revision_number` | INTEGER | NOT NULL, `> 0` |
| `ciphertext` | BYTEA | NOT NULL, `>= 16` bytes |
| `nonce` | BYTEA | NOT NULL, exactly 12 bytes |
| `client_mutation_id` | UUID | NOT NULL |

Constraints:

- `ck_response_answer_revisions_revision_number_valid`  -  `revision_number >
  0`.
- `ck_response_answer_revisions_ciphertext_len`  -  `octet_length(ciphertext)
  >= 16`.
- `ck_response_answer_revisions_nonce_len`  -  `octet_length(nonce) = 12`.
- `fk_response_answer_revisions_answer_same_envelope`  -  `(answer_id,
  envelope_id)` -> `response_answers(id, envelope_id)` ON DELETE CASCADE.
- `uq_response_answer_revisions_id_answer_id`  -  `UNIQUE (id, answer_id)`.
  Lets `response_answers.latest_revision_id` target a revision+answer pair.
- `uq_response_answer_revisions_answer_id_revision_number`  -  `UNIQUE
  (answer_id, revision_number)`. Revision numbers are strictly ordered per
  answer.
- `uq_response_answer_revisions_envelope_id_nonce`  -  `UNIQUE (envelope_id,
  nonce)`. Prevents nonce reuse within an envelope (AES-GCM safety).
- `uq_response_answer_revisions_answer_id_client_mutation_id`  -  `UNIQUE
  (answer_id, client_mutation_id)`. Makes client-driven answer writes
  idempotent.

A deferred FK, added after both tables exist:

- `fk_response_answers_latest_revision_same_answer`  -  `(latest_revision_id,
  id)` -> `response_answer_revisions(id, answer_id)`, `DEFERRABLE INITIALLY
  DEFERRED`. Lets a new answer row and its first revision be inserted in the
  same transaction without a chicken-and-egg ordering problem.

---

## 4. Core/response linkage

There are **no foreign keys between the core and response databases**  -  they
are physically separate Postgres databases and cannot reference each other at
the SQL level.

The link is a cryptographic one: `response_envelopes.session_locator` is an
**HMAC-derived value** computed from `submission_sessions.id` and
`submission_sessions.linkage_key_version` (per
[cryptography-plan.md](cryptography-plan.md) and
[architecture.md](architecture.md)).
Given a `submission_sessions` row, the service layer derives the
corresponding `session_locator` and looks up the matching
`response_envelopes` row by that derived value  -  `response_envelopes` has no
column that stores a plaintext or foreign-keyed session id.

> **Discrepancy from the root repo guide**: the root repo guide describes the
> core/response link as "a shared integer
> (`core.survey_submissions.id <-> response.submissions.core_submission_id`)".
> That describes the **pre-Phase-1 legacy model**, which used a
> `survey_submissions`/`submissions` table pair with a shared integer id and
> a direct (cross-database, enforced only at the application layer) id
> correspondence. **The current model has no `survey_submissions` table, no
> `submissions` table, and no `core_submission_id` column.** The anchor is
> `submission_sessions.id`, and the cross-database link is the derived
> `session_locator`, not a shared integer id. The root guide's
> architecture description is stale with respect to this area and should be
> updated separately.

### Why the response DB never stores a real `user_id`

The response database is the privacy boundary: it stores encrypted answer
content with no column that can be joined back to `users`, `project_subjects`,
or any other core identity table without the HMAC derivation (which itself
requires the linkage key, not stored in the response database). This means a
compromise of the response database alone does not directly expose which
respondent submitted which answers  -  an attacker would also need the core
database and the linkage key material to correlate `session_locator` values
back to `submission_sessions` rows and from there to `project_subjects` /
`project_subject_identities`.

---

## 5. Key invariants / constraints summary

| Invariant | Constraint(s) | Table |
|---|---|---|
| Browser session token hash is globally unique | `uq_submission_sessions_browser_session_token_hash` | `submission_sessions` |
| Session status is one of three values, consistent with `completed_at` | `ck_submission_sessions_session_status_valid`, `ck_submission_sessions_completed_at_consistent` | `submission_sessions` |
| Timestamps ordered: `started_at <= completed_at <= last_activity_at`, `expires_at > started_at` | `ck_submission_sessions_completed_at_after_started_at`, `ck_submission_sessions_completed_before_last_activity`, `ck_submission_sessions_expires_at_after_started_at`, `ck_submission_sessions_last_activity_at_after_started_at` | `submission_sessions` |
| `session_locator` is globally unique and exactly 32 bytes | `uq_response_envelopes_session_locator`, `ck_response_envelopes_session_locator_len` | `response_envelopes` |
| Answer locator unique within its envelope | `uq_response_answers_envelope_id_answer_locator` | `response_answers` |
| Nonce never reused within an envelope | `uq_response_answer_revisions_envelope_id_nonce` | `response_answer_revisions` |
| Revision numbers strictly ordered per answer | `uq_response_answer_revisions_answer_id_revision_number` | `response_answer_revisions` |
| Answer writes idempotent per client mutation | `uq_response_answer_revisions_answer_id_client_mutation_id` | `response_answer_revisions` |
| At most one active authenticated identity per project per user | `uq_project_subject_identities_active_user` | `project_subject_identities` |
| No duplicate active email on one subject | `uq_project_subject_identities_subject_active_email` | `project_subject_identities` |
| At most one verified active email owner per project | `uq_project_subject_identities_project_verified_email` | `project_subject_identities` |
| One participant per subject per project | `uq_project_participants_project_subject` | `project_participants` |
| Participant's identity must belong to participant's subject (same project) | `fk_project_participants_identity_same_subject` | `project_participants` |
| `survey_links.link_type` gates assignment requirements | `ck_survey_links_link_type_valid`, `ck_survey_links_general_has_no_assignment`, `ck_survey_links_assigned_requires_participant`, `ck_survey_links_used_at_requires_assignment` | `survey_links` |

---

## Sources

- `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
- `infra/postgres/init/schema/flowform_response_db_schema_v4.sql`
- `backend/app/schema/orm/core/` (ORM models)
- `backend/app/schema/enums.py`
- Current SQL schema files and ORM models listed above
