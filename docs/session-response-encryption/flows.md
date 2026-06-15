# Respondent-Facing Flows (as currently implemented)

This document consolidates the respondent-facing flows against the code as it
exists today. It supersedes earlier phase notes where they describe behavior
that has since changed or has not yet been built.

## 1. Overview

Respondent flows fall into two groups:

- **Implemented**  -  link resolution, subject resolution, and session start
  are fully wired: `POST /links/resolve`, `POST /links/verification/link`,
  and `POST /submission-sessions` all run through real domain/service code
  and write to the database.
- **Stubbed**  -  `GET /submission-sessions/current`,
  `PUT /submission-sessions/current/answers/<question_node_id>`,
  `POST /submission-sessions/current/events/question-viewed`, and
  `POST /submission-sessions/current/complete` are placeholders marked with
  `TODO(phaseN)` comments in `backend/app/api/v1/public.py`. They return
  stable, schema-valid stub responses but do not read or write session state.

## 2. Link resolution flow

`POST /links/resolve` -> `SurveyLinkService.resolve_link`
(`backend/app/services/public_links.py`):

1. The raw token is resolved to a `SurveyLink` row via
   `plr.resolve_token` (`backend/app/repositories/public_link_repo.py`).
   A miss raises `LinkNotFoundError`.
2. The resolved link is checked by the shared rule function
   `submission_access_rules.ensure_link_token_access(db, project_id=..., link=..., actor=...)`
   (`backend/app/domain/submission_access_rules.py`).

`ensure_link_token_access` performs, in order:

- `public_link_rules.ensure_is_active(link=link)`
- `public_link_rules.ensure_not_expired(link=link)`
- `public_link_rules.ensure_auth_satisfied(link=link, actor=actor)`
- `public_link_rules.ensure_not_used(link=link)`

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
`SurveyAccessResolver._resolve_link`
(`backend/app/services/submissions/access_resolver.py`) when resolving a link
token for `POST /submission-sessions`. This means session start now enforces
the **same authenticated-link checks** as `POST /links/resolve`  -  a
behavior change from the earlier split implementation. Previously these two
entry points could diverge; now both go through one shared rule, so an
authenticated link that isn't usable via `/links/resolve` is also rejected at
session start with the same error codes.

### Separate verification flow

`POST /links/verification/link` ->
`SurveyLinkService.verify_authenticated_link_participant` ->
`ParticipantService.verify_participant_for_user`
(`backend/app/services/participants.py`). This is the flow that *creates* the
authenticated-user identity link in the first place (an email-match rule
between the actor and the participant's stored email). It is distinct from
`ensure_link_token_access`, which only *checks* that such an identity already
exists and matches the actor  -  it does not create or update identities.

## 3. Subject resolution flow

`ProjectSubjectResolver.resolve`
(`backend/app/services/submissions/project_subject_resolver.py`) resolves an
optional `ResolvedProjectSubject` using only server-owned context, in this
precedence order:

1. **Assigned link**  -  if `link is not None and link.assigned_participant_id is not None`:
   load `link.assigned_participant` (raises `SubjectResolutionError` if
   missing), then `_require_subject(db, project_id=..., subject_id=participant.project_subject_id)`.
   Returns `ResolvedProjectSubject(subject=subject, source="assigned_link")`.

2. **Authenticated user identity**  -  else if `actor is not None`: look up
   `psir.get_active_user_identity(db, project_id=..., user_id=actor.id)`
   (`backend/app/repositories/core/project_subject_identities.py`). If found,
   `_require_subject(db, project_id=..., subject_id=identity.project_subject_id)`.
   Returns `ResolvedProjectSubject(subject=subject, source="authenticated_user")`.

3. **Recognition token**  -  else if `recognition_token is not None`:
   `pstr.get_active_token(db, project_id=..., raw_token=recognition_token)`.
   If found, `_require_subject(...)`, then `pstr.mark_used(db, token=token)`.
   Returns `ResolvedProjectSubject(subject=subject, source="recognition_token")`.

4. **Anonymous subject creation**  -  else if `create_anonymous_subject=True`:
   `psr.create_subject(db, project_id=project_id)`, returns
   `ResolvedProjectSubject(subject=subject, source="anonymous_created")`.
   **This branch is not used by the live v1 session-start flow**  -
   `SessionStarter.start` always calls `resolve(...)` with
   `create_anonymous_subject=False`. Anonymous public/general-link sessions
   therefore keep `submission_sessions.project_subject_id = NULL` unless a
   server-owned context resolves a real subject.

5. **None**  -  otherwise, returns `ResolvedProjectSubject(subject=None, source="none")`.

`_require_subject` calls `psr.get_subject(db, project_id=..., subject_id=...)`
and raises `SubjectResolutionError` if the row is missing. This is a
server-invariant guard, not a normal-path outcome: the schema's composite
foreign keys should make a dangling `project_subject_id` reference impossible,
so a miss here indicates a broken invariant rather than a reason to silently
fall back to an anonymous session.

V1 policy: anonymous access does not create `project_subjects` rows by default.
The explicit `create_anonymous_subject=True` branch remains available for future
flows that deliberately need a project-scoped subject before identity,
recognition-cookie, or IP-observation policy is expanded.

## 4. Session start flow

`POST /submission-sessions` -> `SessionStarter.start`
(`backend/app/services/submissions/session_starter.py`):

1. `SurveyAccessResolver.resolve(db, payload=payload, actor=actor)` resolves
   either a `public_slug` or a link `token` into a `SubmissionAccessGrant`
   (`survey`, `published_version`, and optional `link`). For the link path
   this runs `ensure_link_token_access` as described above (section 2).
2. `survey_rules.ensure_has_response_store(survey=access.survey)` confirms the
   survey has a linked response store, returning `response_store_id`.
3. `ProjectSubjectResolver.resolve(db, project_id=access.survey.project_id, link=access.link, actor=actor, recognition_token=recognition_token, create_anonymous_subject=False)`
   resolves the optional subject (section 3). `resolved_subject.subject` may
   be `None`.
4. `ssr.generate_browser_session_token()` generates a raw browser session
   token.
5. `ssr.create_session(...)` inserts a `submission_sessions` row:
   - `survey_version_id` is the **frozen** `published_version.id`
   - `link_id` is `access.link.id` if a link was used, else `None`
   - `project_subject_id` is `subject.id` if resolved, else `None`
     (anonymous session)
   - the browser session token is stored hashed
   - `response_store_id` from step 2
6. If `access.link is not None and access.link.is_single_use`,
   `plr.mark_used(db, link=access.link)` marks the link consumed. Only
   single-use (assigned) links are marked used here  -  stamping `used_at` on
   an unassigned reusable link would violate
   `ck_survey_links_used_at_requires_assignment`.
7. `commit_with_err_handle(db, contexts=[session])` commits the transaction.
8. A `PublicSubmissionSessionResponses` is built from the session and grant:
   `status`, `started_at`, `expires_at`, a `survey` summary (`id`, `title`), a
   `version` summary (`id`, `version_number`, `compiled_schema`), and an empty
   `answers` list.
9. The route (`backend/app/api/v1/public.py`,
   `start_submission_session`) calls `set_submission_session_cookie` on the
   response to set the HttpOnly resume-token cookie from the raw browser
   session token, and returns 201.

**Note on encryption machinery**: the current implementation has **no
response-envelope, DEK, or KMS logic**. Per-session envelope creation during
session start is an aspirational design that has not been implemented  -  it
is omitted here as "not yet implemented."

## 5. Stubbed flows

All four endpoints below live in `backend/app/api/v1/public.py` and are
explicitly marked with `TODO(phaseN)` comments. They currently return stable,
schema-valid placeholder responses with no session-state reads or writes.

### `GET /submission-sessions/current`

`TODO(phase3)`. Currently returns `build_placeholder_session_response()`
unconditionally  -  no cookie is read.

**Intended**: read the resume-token
cookie, hash it, look up the matching `submission_sessions` row, load the
session's canonical answers, and build the real
`PublicSubmissionSessionResponses` (including the persisted `answers` list).

### `PUT /submission-sessions/current/answers/<question_node_id>`

`TODO(phase4)`. Currently parses `SaveSubmissionSessionAnswerRequest` and
echoes the payload back as a `SubmissionSessionAnswerResponses` with a
hardcoded `revision_number=1` and `saved_at=datetime.now(UTC)`  -  nothing is
persisted.

**Intended**: resolve the response
envelope/DEK for the session, locate the answer slot for
`question_node_id` against the frozen survey version's compiled schema,
insert a new answer revision, and enforce idempotency via
`client_mutation_id` (a repeat request with the same `client_mutation_id`
should return the existing revision rather than creating a new one).

### `POST /submission-sessions/current/events/question-viewed`

`TODO(phase3)`. Currently parses `QuestionViewedEventRequest` and returns
`204` with no body  -  nothing is persisted.

**Intended**: insert a
`question_viewed` analytics event row on the core side. This write should be
non-blocking  -  a failure to record the event must not fail the respondent's
request.

### `POST /submission-sessions/current/complete`

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
  answer save. None of this exists in
  `session_starter.py` or in the stubbed answer-save endpoint today. Treat
  those sections as the target design for phase 4+, not current behavior.

- **`assigned_subject_id` -> `assigned_participant_id`**  -  earlier drafts of
  the session/link docs referenced a (dead) `assigned_subject_id` field on
  `SurveyLink`. The current schema and code use
  `link.assigned_participant_id`, with the subject reached indirectly via
  `participant.project_subject_id` (section 3, step 1). This doc reflects the
  corrected field name throughout.

- **Session-start / link-resolve unification**  -  prior to
  the current shared-rule implementation, `POST /submission-sessions` and
  `POST /links/resolve` could enforce different rules for authenticated links.
  Both now call the same
  `submission_access_rules.ensure_link_token_access` (section 2), so the
  error codes (`LINK_ASSIGNED_PARTICIPANT_REQUIRED`,
  `LINK_PARTICIPANT_VERIFICATION_REQUIRED`, `LINK_ASSIGNED_TO_ANOTHER_USER`)
  are consistent across both endpoints.

- **Anonymous subject creation policy**  -  `ProjectSubjectResolver`'s
  `create_anonymous_subject=True` branch (section 3, step 4) exists in code
  but is not used by `SessionStarter.start`. V1 keeps anonymous public/general
  link sessions as `project_subject_id = NULL`; creating anonymous subject rows
  is reserved for a future flow with explicit product policy.
