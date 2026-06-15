# API Surface  -  Current State

This document is a **verified-against-code snapshot** of the public REST API
surface relevant to the session-response-encryption work, as of the current
backend implementation. It consolidates and corrects the older API,
backend-implementation, admin/operations, and phase-comment notes.

> **Relationship to other docs.** This document describes *what exists in
> code right now* (real vs. placeholder), not the full target design. For
> respondent flow details, see [flows.md](flows.md). For save-ordering,
> response-envelope, and crypto/locator work that is still pending, see
> [remaining-work.md](remaining-work.md) and
> [cryptography-plan.md](cryptography-plan.md).

---

## 1. Public survey discovery routes

Source: `backend/app/api/v1/public.py`

| Method | Path | Status |
|---|---|---|
| `GET` | `/api/v1/public/surveys` | Real  -  list public surveys |
| `GET` | `/api/v1/public/surveys/{public_slug}` | Real  -  get single survey + published version |

Both are reused as-is. `GET /surveys/{public_slug}` returns the survey and
its currently published version, including `compiled_schema`
(`SurveyVersionResponses.compiled_schema`).

---

## 2. Submission session routes

Source: `backend/app/api/v1/public.py`

| Method | Path | Status |
|---|---|---|
| `POST` | `/api/v1/public/submission-sessions` | **Real** |
| `GET` | `/api/v1/public/submission-sessions/current` | **Placeholder** (`TODO(phase3)`) |
| `PUT` | `/api/v1/public/submission-sessions/current/answers/{question_node_id}` | **Placeholder** (`TODO(phase4)`) |
| `POST` | `/api/v1/public/submission-sessions/current/events/question-viewed` | **Placeholder** (`TODO(phase3)`) |
| `POST` | `/api/v1/public/submission-sessions/current/complete` | **Placeholder** (`TODO(phase5)`) |

### 2.1 `POST /submission-sessions`  -  real

Implemented via `SessionStarter.start()`. Accepts `StartSubmissionSessionRequest`,
a discriminated union on `access.type`:

```json
{ "access": { "type": "public_slug", "public_slug": "customer-intake" } }
```

```json
{ "access": { "type": "link_token", "token": "plaintext-link-token" } }
```

Auth is optional (`@auth.optional_auth()`). The handler resolves the optional
current user, calls `SessionStarter.start(core_db, payload=payload, actor=user)`,
and returns `201` with a `PublicSubmissionSessionResponses` body. The raw
browser session token returned by the starter is set via
`set_submission_session_cookie()` (`HttpOnly`, resume cookie), matching the
session-start flow summarized in [flows.md](flows.md).

### 2.2 `GET /submission-sessions/current`  -  placeholder

Marked `TODO(phase3)`. Current behavior:

- Ignores the resume cookie entirely.
- Returns `build_placeholder_session_response()`  -  a static stub  -  with `200`.

Intended final behavior: read the
`HttpOnly` resume cookie, hash it (`SHA-256`), load the session by
`browser_session_token_hash`, check status/expiry, derive the response
locator, load and decrypt canonical latest revisions, and return
`PublicSubmissionSessionResponses` with populated `answers`.

### 2.3 `PUT /submission-sessions/current/answers/{question_node_id}`  -  placeholder

Marked `TODO(phase4)`. Current behavior:

- Parses `SaveSubmissionSessionAnswerRequest` (validates request shape only).
- Echoes the input straight back as `SubmissionSessionAnswerResponses`, with
  `revision_number` hardcoded to `1` and `saved_at=datetime.now(UTC)`.
- Does **not** persist anything  -  no response-DB write, no core session update.

Intended final behavior: validate the question node against the frozen survey
version, then follow this save ordering:

```text
1. Lock and validate the core session.
2. Update core last_activity_at.
3. Save the encrypted response revision.
4. Commit the response transaction.
5. Insert the core answer_saved analytics event.
6. Commit the core transaction.
7. Return success.
```

The response write (step 3/4) is authoritative; the analytics insert
(steps 5-6) is secondary. Real revision numbering and `client_mutation_id`
based idempotency replace the current hardcoded `revision_number=1`.

### 2.4 `POST /submission-sessions/current/events/question-viewed`  -  placeholder

Marked `TODO(phase3)`. Current behavior:

- Parses `QuestionViewedEventRequest` (validates request shape only).
- Returns `204` with no persistence.

Intended final behavior: validate
the node belongs to the frozen version and insert a core `question_viewed`
analytics event. This is secondary metadata  -  if the insert fails, the
respondent must still continue (non-blocking failure).

### 2.5 `POST /submission-sessions/current/complete`  -  placeholder

Marked `TODO(phase5)`. Current behavior:

- Returns a fabricated `CompleteSubmissionSessionResponses` with
  `status="completed"` and `completed_at=datetime.now(UTC)`.
- Does **not** persist or lock the session, and does not check whether a
  session was ever started.

Intended final behavior: lock the
session, return the existing completion if already completed (idempotent),
validate the final canonical answer set, mark the session `completed`, set
`completed_at`, insert a `session_completed` event, and reject later edits.

---

## 3. Removed/deprecated routes

Older API notes described `POST /api/v1/public/submissions/slug` and
`POST /api/v1/public/submissions/link` as "still present, marked with
decommission TODOs" pending removal.

**This is stale.** As of the current `backend/app/api/v1/public.py`, neither
route exists:

```text
POST /api/v1/public/submissions/slug    ->  not present (already removed)
POST /api/v1/public/submissions/link    ->  not present (already removed)
```

There is no remaining trace of these routes  -  no decommission TODO markers,
no `SubmissionIntakeService` import, no route registration. They were fully
removed, not merely deprecated or returning `410 Gone`. Any doc describing
these as a pending removal step should be considered stale; the migration
step they describe is already complete.

---

## 4. Public link routes

### 4.1 Survey link management (Studio-authenticated)

Source: `backend/app/api/v1/projects/public_links.py`, under
`/projects/{project_id}/surveys/{survey_id}/links`. All real.

| Method | Path | Status |
|---|---|---|
| `GET` | `/links` | Real  -  list links |
| `POST` | `/links` | Real  -  create link (returns plaintext token once) |
| `PATCH` | `/links/{link_id}` | Real  -  update link |
| `DELETE` | `/links/{link_id}` | Real  -  delete link |

`POST /links` returns `CreatePublicLinkResponses` containing the link, the
one-time plaintext `token`, and a constructed `url`.

### 4.2 `POST /api/v1/public/links/resolve`  -  real

Body-based `ResolveTokenRequest`:

```json
{ "token": "plaintext-link-token" }
```

Auth is optional (`@auth.optional_auth()`). Resolves token hash -> active ->
expiry -> auth-required -> assigned-email -> single-use -> survey -> published
version via `SurveyLinkService.resolve_link()`. This is a **preview**, not an
authorization grant  -  `POST /submission-sessions` revalidates the link. This
already matches the verb-change decision described in [flows.md](flows.md)
(the route was `GET ...?token=`; it is now `POST` with the token in the body).

### 4.3 `POST /api/v1/public/links/verification/link`  -  real, authenticated

Requires `@auth.require_auth()`. Body is also `ResolveTokenRequest`. Verifies
the authenticated account against the participant identity assigned to an
authenticated survey link  -  the account email must match the participant
identity email before the participant is linked to the user, via
`SurveyLinkService.verify_authenticated_link_participant()`. Returns
`PublicLinkResponses`. Full flow detail is in
[flows.md](flows.md); this section only documents the
contract.

---

## 5. Admin/operator response-viewing routes

Source: `backend/app/api/v1/projects/survey_responses.py` and
`survey_responses_temp.py`.

**Correction to earlier planning notes:** these routes are **not absent**  - 
they exist and are registered, but every handler is a `TODO(phase7)` contract
stub backed by `survey_responses_temp.py`'s `build_placeholder_*` helpers.

| Method | Path | Status |
|---|---|---|
| `GET` | `/projects/{project_id}/surveys/{survey_id}/responses` | **Placeholder**  -  returns empty page (`PaginatedSurveyResponsesResponses(items=[], total=0, ...)`) |
| `GET` | `/projects/{project_id}/surveys/{survey_id}/responses/{session_id}` | **Placeholder**  -  returns `SurveyResponseDetailResponses` with a synthetic session summary and `answers=[]` |
| `GET` | `/projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history` | **Placeholder**  -  returns `SurveyResponseHistoryResponses` with a synthetic session summary and `revisions=[]` |
| `POST` | `/projects/{project_id}/surveys/{survey_id}/responses/export` | **Placeholder**  -  returns `202` with `SurveyResponseExportResponses(download_url=None)`, no file produced |
| `DELETE` | `/projects/{project_id}/surveys/{survey_id}/responses/{session_id}` | **Placeholder**  -  returns `204`, no actual deletion |

All five routes are gated by `@auth.require_auth()` and
`@require_survey_permission(PERMISSIONS.submission.view)`. The response
**shapes are final**  -  Studio can wire its results view against them now  -  but
no handler authorizes survey access against real session data, derives the
session locator, loads the response envelope, or decrypts canonical
revisions. The code comment in `survey_responses.py` is explicit:

> `TODO(phase7)`: Replace these contract stubs with the real admin-read
> service. Every handler must authorise survey access, derive the session
> locator from core metadata, load the response envelope, and decrypt
> canonical revisions through the service path  -  never bypassing the
> decrypt/authorisation flow.

For the remaining work, see [remaining-work.md](remaining-work.md).

---

## 6. Summary table

| Route | Status |
|---|---|
| `GET /public/surveys` | Real |
| `GET /public/surveys/{public_slug}` | Real |
| `POST /public/links/resolve` | Real |
| `POST /public/links/verification/link` | Real (authenticated) |
| `POST /public/submission-sessions` | Real |
| `GET /public/submission-sessions/current` | Placeholder (phase3) |
| `PUT /public/submission-sessions/current/answers/{question_node_id}` | Placeholder (phase4) |
| `POST /public/submission-sessions/current/events/question-viewed` | Placeholder (phase3) |
| `POST /public/submission-sessions/current/complete` | Placeholder (phase5) |
| `POST /public/submissions/slug` | Removed (fully gone) |
| `POST /public/submissions/link` | Removed (fully gone) |
| `GET /projects/{project_id}/surveys/{survey_id}/links` | Real |
| `POST /projects/{project_id}/surveys/{survey_id}/links` | Real |
| `PATCH /projects/{project_id}/surveys/{survey_id}/links/{link_id}` | Real |
| `DELETE /projects/{project_id}/surveys/{survey_id}/links/{link_id}` | Real |
| `GET /projects/{project_id}/surveys/{survey_id}/responses` | Placeholder (phase7) |
| `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}` | Placeholder (phase7) |
| `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history` | Placeholder (phase7) |
| `POST /projects/{project_id}/surveys/{survey_id}/responses/export` | Placeholder (phase7) |
| `DELETE /projects/{project_id}/surveys/{survey_id}/responses/{session_id}` | Placeholder (phase7) |
