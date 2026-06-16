# Respondent-Facing Flows (as currently implemented)

This document consolidates the respondent-facing flows against the code as it
exists today. It supersedes earlier phase notes where they describe behavior
that has since changed or has not yet been built.

## 1. Overview

Respondent flows fall into two groups:

- **Implemented**  -  link resolution, subject resolution, and session start
  are fully wired: `POST /links/resolve`, `POST /links/verification/link`,
  and `POST /submission-session/start` all run through real domain/service code
  and write to the database.
- **Stubbed command routes**  -  `PUT /submission-session/answer`,
  `POST /submission-session/event`, and `POST /submission-session/complete` are
  placeholders marked with `TODO(phaseN)` comments in
  `backend/app/api/v1/public.py`. They return stable, schema-valid stub
  responses but do not read or write session state.
- **Not present by design**  -  there is no public current-session read route.
  Cookie-backed session lookup is intended as an internal guard for command
  routes, not a respondent data-rehydration endpoint.

### Service class map

| Concern | Class | File |
|---|---|---|
| Session lifecycle (start/answer/event/complete) | `SessionManagementService` | `services/public_submissions/api/session_management.py` |
| Survey browsing, link resolution, account linking | `SurveyResolveService` | `services/public_submissions/api/survey_resolve.py` |
| Access grant from slug or link token | `AccessResolver` | `services/public_submissions/core/access_resolver.py` |
| Subject priority waterfall + merge/token instructions | `SubjectResolver` | `services/public_submissions/core/subject_resolver.py` |
| Recognition token lifecycle | `SubjectTokenService` | `services/public_submissions/core/subject_token.py` |
| Full session-start orchestration | `SessionStarter` | `services/public_submissions/core/session_starter.py` |

## 2. Link resolution flow

`POST /links/resolve` -> `SurveyResolveService.resolve_link`
(`backend/app/services/public_submissions/api/survey_resolve.py`):

1. The raw token is resolved to a `SurveyLink` row via
   `plr.resolve_token` (`backend/app/repositories/public_link_repo.py`).
   A miss raises `LinkNotFoundError`.
2. `AccessResolver.resolve_link_token(db, link=link, actor=actor)` is called,
   which runs
   `submission_access_rules.ensure_link_token_access(db, project_id=..., link=..., survey=..., actor=...)`
   (`backend/app/domain/submission_access_rules.py`).

`ensure_link_token_access` performs, in order:

- `public_link_rules.ensure_is_active(link=link)`
- `public_link_rules.ensure_not_expired(link=link)`
- `public_link_rules.ensure_auth_satisfied(link=link, actor=actor)`
- `public_link_rules.ensure_not_used(link=link)`
- `public_link_rules.ensure_link_allowed_by_survey_visibility(survey=survey, link=link)`  -  a
  general (unassigned) link on a `visibility="private"` survey raises
  `PrivateSurveyAssignedEmailRequiredError`.

If `actor is None` or `link.link_type != "authenticated"`, the function
returns here  -  no participant checks apply.

For an **authenticated link** accessed by a **logged-in actor**:

- If `link.assigned_participant_id is None`, raises
  `LinkAuthAssignmentRequiredError` (422, `LINK_ASSIGNED_PARTICIPANT_REQUIRED`)
   -  "Links that require authentication must be assigned to a participant."
- Otherwise the assigned participant is loaded
  (`ppr.get_participant`); a missing row also raises
  `LinkAuthAssignmentRequiredError` via `ensure_present`.
- `public_link_rules.ensure_participant_identity_authenticated(identity=identity)`
   -  if the participant's identity is not an authenticated-user identity,
  raises `LinkParticipantVerificationRequiredError` (403,
  `LINK_PARTICIPANT_VERIFICATION_REQUIRED`)  -  "This link's participant must
  complete verification before this link can be used."
- `public_link_rules.ensure_actor_matches_participant_identity(identity=identity, actor=actor)`
   -  if the identity's `user_id` does not match `actor.id`, raises
  `LinkAssignmentMismatchError` (403, `LINK_ASSIGNED_TO_ANOTHER_USER`)  -  "This
  link is assigned to a different user."

### Unification with session start

`ensure_link_token_access` is the same function called by
`AccessResolver.resolve_link_token`
(`backend/app/services/public_submissions/core/access_resolver.py`) when
resolving a link token for `POST /submission-session/start`. This means session
start enforces the **same checks** as `POST /links/resolve`  -  link state,
visibility compatibility, and authenticated-link participant identity  -  so an
authenticated link that isn't usable via `/links/resolve` is also rejected at
session start with the same error codes.

### Separate verification flow

`POST /links/verification/link` ->
`SurveyResolveService.verify_authenticated_link_participant`
(`backend/app/services/public_submissions/api/survey_resolve.py`) ->
`ParticipantService.verify_participant_for_user`
(`backend/app/services/participants.py`). This is the flow that *creates* the
authenticated-user identity link in the first place (an email-match rule
between the actor and the participant's stored email).

After linking the identity, `verify_authenticated_link_participant` also
reconciles the browser recognition token: it calls `SubjectResolver.resolve_assigned_subject`
to determine the correct token action (keep, rotate, or issue), applies any
canonical merge if the token subject differs from the assigned subject, and
applies the token action via `SubjectTokenService.apply_token_action`. The raw
recognition token is returned to the route only when it has changed (i.e. when
the action is `issue` or `rotate`).

This is distinct from `ensure_link_token_access`, which only *checks* that an
authenticated identity already exists and matches the actor  -  it does not
create or update identities.

## 3. Subject resolution flow

`SubjectResolver.resolve`
(`backend/app/services/public_submissions/core/subject_resolver.py`) routes to
one of two paths based on `access_method`, then returns a
`SubjectResolutionResult` carrying `final_subject_id`, `subject_source`,
`token_action`, and optional merge instructions. The caller (`SessionStarter`)
applies all writes before committing.

Recognition-token lookup is performed **before** `SubjectResolver.resolve` is
called: `SubjectTokenService.lookup` resolves the raw token to a
`RecognitionTokenLookupResult` (read-only; does not stamp `last_used_at`), and
the resulting `token_subject_id` / `canonical_token_subject_id` are passed in.

### 3a. Assigned-access path (private link, authenticated link)

The assigned subject always wins. The token is used only for continuity cleanup.

1. Load the assigned subject via `_require_subject`. A miss raises
   `SubjectResolutionError` (server invariant violation).
2. Resolve to canonical via `_resolve_to_canonical` (one-hop follow of
   `canonical_subject_id`; canonical chains are not allowed).
3. If no recognition token: `token_action="issue"`, return
   `source="assigned_link"`.
4. Resolve the token candidate to its canonical (`canonical_token_subject_id or
   token_subject_id`).
5. If the token canonical **matches** the assigned canonical:
   - Token points directly at canonical → `token_action="keep"`.
   - Token points at a non-canonical that resolves to canonical → `token_action="rotate"`.
6. If the token canonical **differs**: `token_action="rotate"`, set
   `merge_subject_id=effective_token_subject_id`,
   `merge_into_subject_id=canonical_assigned.id` (the caller merges the token
   subject into the assigned subject before committing).

### 3b. Open-access path (public slug, general link)

Priority waterfall: logged-in identity > recognition token > new anonymous subject.

**No actor, no token**: `subjects.create_subject(...)` creates a new
`project_subjects` row and `token_action="issue"`. Anonymous public/general-link
sessions always get a new subject row  -  `project_subject_id` is never `NULL`
for open-access sessions.

**Token, no actor**: `final_subject_id = canonical_token_subject_id or
token_subject_id`, `token_action="mark_used"`.

**Actor present**: `sub_id.get_active_user_identity(...)` is looked up.

- **No identity, token present**: attach identity to the token subject
  (`final_subject_id = effective_token_subject_id`, `needs_identity_write=True`,
  `token_action="mark_used"`). Caller writes the identity row.
- **No identity, no token**: create a new subject, `needs_identity_write=True`,
  `token_action="issue"`.
- **Identity found**: resolve to canonical. Then:
  - No token → `token_action="issue"`.
  - Token canonical matches identity canonical → `keep` (direct hit) or `rotate`
    (non-canonical hit).
  - Token canonical differs → `token_action="rotate"`, merge token subject into
    identity subject.

`_require_subject` raises `SubjectResolutionError` if a referenced subject row
is missing. This is a server-invariant guard  -  composite FKs make a dangling
reference structurally impossible, so a miss indicates a broken invariant.

## 4. Session start flow

`POST /submission-session/start` -> `SessionManagementService.start_session`
-> `SessionStarter.start`
(`backend/app/services/public_submissions/core/session_starter.py`):

1. `AccessResolver.resolve(db, payload=payload, actor=actor)` resolves
   either a `public_slug` or a link `token` into a `SubmissionAccessGrant`
   (`survey`, `published_version`, `access_method`, and optional `link`). For
   the link path this runs `ensure_link_token_access` as described in section 2.
2. `survey_rules.ensure_has_response_store(survey=access.survey)` confirms the
   survey has a linked response store, returning `response_store_id`.
3. **Recognition token lookup (read-only)**: if a raw `recognition_token` was
   passed, `SubjectTokenService.lookup(db, project_id=..., raw_token=...)` is
   called. This resolves the token to `token_subject_id` and
   `canonical_token_subject_id` without touching `last_used_at`. Invalid or
   absent tokens produce `token_subject_id=None`.
4. `SubjectResolver.resolve(db, project_id=..., access_method=...,
   assigned_subject_id=..., token_subject_id=..., canonical_token_subject_id=...,
   actor_user_id=...)` returns a `SubjectResolutionResult` (section 3).
   `final_subject_id` is always set (open-access always creates a new subject
   if no other context resolves one; it is never `None`).
5. **Apply canonical merge** (if instructed): if `resolution.merge_subject_id`
   and `resolution.merge_into_subject_id` are set, `subjects.set_canonical_subject`
   is called to point the weaker subject at the stronger one before any other
   write.
6. **Apply identity write** (if instructed): if `actor is not None` and
   `resolution.needs_identity_write`, `sub_id.create_user_identity(...)` writes a
   new `project_subject_identities` row linking the actor to the final subject.
7. **Apply token mechanics**: `SubjectTokenService.apply_token_action(db, ...,
   token_action=resolution.token_action, existing_raw_token=recognition_token)`
   executes the instruction from the resolver:
   - `issue` — create a new token, return raw token.
   - `rotate` — revoke existing token for final subject, issue new one, return raw token.
   - `mark_used` — stamp `last_used_at` on the existing token, return existing raw token.
   - `keep` / `none` — no write, return `None`.
8. `ssr.generate_browser_session_token()` generates a raw browser session token.
9. `ssr.create_session(...)` inserts a `submission_sessions` row:
   - `survey_version_id` is the **frozen** `published_version.id`
   - `link_id` is `access.link_id` if a link was used, else `None`
   - `project_subject_id` is `resolution.final_subject_id`
   - the browser session token is stored hashed
   - `response_store_id` from step 2
10. If `access.link is not None and access.is_single_use`,
    `plr.mark_used(db, link=access.link)` marks the link consumed. Only
    single-use (assigned) links are marked used here  -  stamping `used_at` on
    an unassigned reusable link would violate
    `ck_survey_links_used_at_requires_assignment`.
11. `commit_with_err_handle(db, contexts=[session, ...])` commits the transaction.
12. A `PublicSubmissionSessionResponses` is built from the session and grant:
    `status`, `started_at`, `expires_at`, `survey_version_id`, and
    `survey_schema`. `survey_schema` is set to `published_version.compiled_schema`
    for **public-slug** access; it is `None` for all link-based access (the schema
    was delivered at link-resolve time).
13. `SessionStarter.start` returns
    `(session_response, raw_browser_session_token, raw_recognition_token)`. The
    route sets both the browser-session cookie and (when non-`None`) the
    recognition cookie, then returns `201`.

**Note on encryption machinery**: the current implementation has **no
response-envelope, DEK, or KMS logic**. Per-session envelope creation during
session start is aspirational and has not been implemented.

## 5. Stubbed flows

All three endpoints below live in `backend/app/api/v1/public.py` and are
explicitly marked with `TODO(phaseN)` comments. They currently return stable,
schema-valid placeholder responses with no session-state reads or writes.

### No public current-session read route

Public mid-session data reads are not part of the respondent API. Cookie-backed
session lookup should become an internal guard used by answer/event/complete
commands, not a route that returns in-process encrypted answer state.

### `PUT /submission-session/answer`

`TODO(phase4)`. Currently parses `SaveSubmissionSessionAnswerRequest` and
echoes the payload back as a `SubmissionSessionAnswerResponses` with a
hardcoded `revision_number=1` and `saved_at=datetime.now(UTC)`  -  nothing is
persisted. `question_node_id` is in the request body.

**Intended**: resolve the response
envelope/DEK for the session, locate the answer slot for
`question_node_id` against the frozen survey version's compiled schema,
insert a new answer revision, and enforce idempotency via
`client_mutation_id` (a repeat request with the same `client_mutation_id`
should return the existing revision rather than creating a new one).

### `POST /submission-session/event`

`TODO(phase3)`. Currently parses `SubmissionSessionEventRequest` and returns
`204` with no body  -  nothing is persisted. The current client event type is
`question_viewed`.

**Intended**: insert a
`question_viewed` analytics event row on the core side. This write should be
non-blocking  -  a failure to record the event must not fail the respondent's
request.

### `POST /submission-session/complete`

`TODO(phase5)`. Currently returns
`CompleteSubmissionSessionResponses(status="completed", completed_at=datetime.now(UTC))`
unconditionally  -  no session is loaded or mutated.

**Intended**: load the current session,
validate the final set of answers against the frozen survey version's
compiled schema, lock the session and mark it `completed`, and be idempotent
(a repeat completion request for an already-completed session should return
the original completion result rather than erroring).

## 6. Conflicts and notes vs. older docs

- **Envelope/DEK/KMS encryption**  -  earlier flow docs described
  response-envelope creation at session start and envelope/DEK lookups during
  answer save. None of this exists in `session_starter.py` or in the stubbed
  answer-save endpoint today. Treat those sections as the target design for
  phase 4+, not current behavior.

- **`assigned_subject_id` -> `assigned_participant_id`**  -  earlier drafts
  referenced a (dead) `assigned_subject_id` field on `SurveyLink`. The current
  schema and code use `link.assigned_participant_id`, with the subject reached
  indirectly via `participant.project_subject_id`. This doc reflects the
  corrected field name throughout.

- **Session-start / link-resolve unification**  -  both
  `POST /submission-session/start` and `POST /links/resolve` now call the same
  `submission_access_rules.ensure_link_token_access`, so error codes
  (`LINK_ASSIGNED_PARTICIPANT_REQUIRED`, `LINK_PARTICIPANT_VERIFICATION_REQUIRED`,
  `LINK_ASSIGNED_TO_ANOTHER_USER`) are consistent across both endpoints. The
  shared function also gained a `survey` parameter and now enforces
  `ensure_link_allowed_by_survey_visibility` (general link + private survey →
  rejected).

- **Anonymous subject creation policy**  -  for open-access flows (public slug,
  general link), `SubjectResolver` always creates a new `project_subjects` row
  when no other context resolves a subject. `submission_sessions.project_subject_id`
  is therefore **never `NULL`** for open-access sessions. Older docs and
  `data-model.md` described a v1 policy of leaving it `NULL`; that was the
  intent of the earlier `ProjectSubjectResolver` with `create_anonymous_subject=False`,
  which no longer exists in this form.

- **Service class renames**  -  `SurveyLinkService` (old) is now
  `SurveyResolveService`. `SurveyAccessResolver` (old) is now `AccessResolver`.
  `ProjectSubjectResolver` (old) is now `SubjectResolver`. File paths under
  `services/submissions/` are now `services/public_submissions/core/` and
  `services/public_submissions/api/`.

- **Recognition token mechanics**  -  earlier docs described token handling as
  a single `mark_used` call inside the resolver. The current implementation
  separates lookup (read-only, `SubjectTokenService.lookup`) from effect
  (`SubjectTokenService.apply_token_action` with `issue | rotate | mark_used |
  keep | none`), and the full token state machine now runs as part of session
  start and account-linking flows.

- **`compiled_schema` in session-start response**  -  public-slug sessions now
  return `survey_schema=published_version.compiled_schema` in the
  `PublicSubmissionSessionResponses`. Link-based sessions return `survey_schema=None`
  (schema was delivered at link-resolve time). Earlier docs stated the response
  never includes `compiled_schema`.
