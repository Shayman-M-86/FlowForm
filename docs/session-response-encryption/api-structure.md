# API Structure

The complete **respondent-facing** API surface for FlowForm submission
sessions. This document is the single reference for the public endpoints a
form-filler's browser calls, from access resolution through session
completion.

It deliberately **excludes** the administrator surface (response viewing,
exports, deletion, RBAC). Those are specified in
[admin-and-operations.md](admin-and-operations.md) and
[backend-implementation.md §30](backend-implementation.md).

> **Scope note.** This document describes the API *shape*. The crypto,
> locator, and cross-database orchestration that sit behind these routes are
> specified in [cryptography.md](cryptography.md),
> [session-flows.md](session-flows.md), and [answer-flows.md](answer-flows.md).
> This document does not restate them — it links to them.

---

## 1. Core flow

```text
Resolve access
    ↓
Start or resume a submission session
    ↓
Load the frozen survey version and current answers
    ↓
Save answer revisions incrementally
    ↓
Record lightweight analytics events
    ↓
Complete the session
```

The existing design establishes that access is resolved before a session is
created, that the backend freezes one published survey version at session
start ([session-flows.md §13.2](session-flows.md)), and that resume restores
**canonical latest answers only** ([session-flows.md §15.4](session-flows.md)).

---

## 2. Session addressing: `current`, never `{session_id}`

Every session route addresses the session as `current`. The session is
identified **server-side** from the `HttpOnly` resume cookie, never from the
URL path.

```text
GET /public/submission-sessions/current
```

not

```text
GET /public/submission-sessions/{session_id}
```

**Why:** the session UUID and resume token must never appear in URLs, where
they would leak into browser history, access logs, and tracing systems
([admin-and-operations.md §33.1](admin-and-operations.md)). The backend reads
the cookie, hashes it (`SHA-256`), and loads the session by
`browser_session_token_hash`. The `session_id` that the locator service needs
([backend-implementation.md §29.2](backend-implementation.md)) is loaded from
that row, never taken from the client.

---

## 3. Required v1 endpoints

```text
GET  /api/v1/public/surveys
GET  /api/v1/public/surveys/{public_slug}

POST /api/v1/public/links/resolve

POST /api/v1/public/submission-sessions
GET  /api/v1/public/submission-sessions/current

PUT  /api/v1/public/submission-sessions/current/answers/{question_node_id}

POST /api/v1/public/submission-sessions/current/events/question-viewed

POST /api/v1/public/submission-sessions/current/complete
```

### 3.1 Public survey discovery *(reuses existing routes)*

| Method | Path | Status |
|---|---|---|
| `GET` | `/api/v1/public/surveys` | **Exists** — reused as-is |
| `GET` | `/api/v1/public/surveys/{public_slug}` | **Exists** — reused as-is |

These let the frontend render a landing page before starting a session. The
session-start endpoint still revalidates the slug — a preview is never trusted.

`GET /surveys/{public_slug}` returns survey + currently published version with
its `compiled_schema` (see `SurveyVersionResponses.compiled_schema`).

### 3.2 Link resolution *(verb change from existing route)*

| Method | Path | Status |
|---|---|---|
| `POST` | `/api/v1/public/links/resolve` | **Changes** existing `GET ...?token=` |

Request:

```json
{ "token": "plaintext-link-token" }
```

Resolves: token hash → active → expiry → auth-required → assigned-email →
single-use → survey → published version. This logic already exists in
`SurveyLinkService.resolve_link()`; only the transport changes.

**This is a behavior change, not a validation of the existing docs.** The
current route is `GET /links/resolve?token=...`. Moving the token to a JSON
body keeps it out of query strings, history, and logs — consistent with
[§33.1](admin-and-operations.md), which treats link tokens as never-loggable.

This endpoint is a **preview**, not an authorization grant. The session-start
endpoint revalidates the link.

### 3.3 Start a session

| Method | Path |
|---|---|
| `POST` | `/api/v1/public/submission-sessions` |

One start route for every access channel — a discriminated union on `type`.
This matches the already-implemented `StartSubmissionSessionRequest` /
`SubmissionSessionAccess` models.

Start through a public slug:

```json
{ "access": { "type": "public_slug", "public_slug": "customer-intake" } }
```

Start through a link token:

```json
{ "access": { "type": "link_token", "token": "plaintext-link-token" } }
```

The backend resolves and revalidates access, freezes `survey_version_id`,
generates a random resume token (storing only its `SHA-256` hash), provisions
the anonymous response envelope, and returns success **only after both
databases succeed** ([session-flows.md §14](session-flows.md)).

Response (`PublicSubmissionSessionResponses`):

```json
{
  "status": "in_progress",
  "started_at": "2026-06-11T01:20:00Z",
  "expires_at": "2026-06-18T01:20:00Z",
  "survey": { "id": 12, "title": "Customer intake" },
  "version": { "id": 31, "version_number": 4, "compiled_schema": {} },
  "answers": []
}
```

Cookie:

```text
Set-Cookie: flowform_submission_session=<random-token>;
  HttpOnly; Secure; SameSite=Lax
```

The backend owns and never accepts from the browser: `session_id`,
`survey_version_id`, `started_at`, `completed_at`, `response_envelope_id`.

### 3.4 Resume / current state

| Method | Path |
|---|---|
| `GET` | `/api/v1/public/submission-sessions/current` |

Resume is the cookie + `GET /current` operation. **There is no separate
`POST /resume` route.** The backend hashes the cookie token, loads the
session, checks status and expiry, derives the response locator, loads
canonical latest revisions, decrypts them, and returns respondent state.

Response is `PublicSubmissionSessionResponses` (same shape as start, with
populated `answers`). Each answer is a `SubmissionSessionAnswerResponses`:
`question_node_id`, `state`, `answer_family`, `answer_value`,
`revision_number`, `client_mutation_id`, `saved_at`.

### 3.5 Save or clear one answer

| Method | Path |
|---|---|
| `PUT` | `/api/v1/public/submission-sessions/current/answers/{question_node_id}` |

The question UUID lives in the **path**, never repeated in the body. Matches
the implemented `SaveSubmissionSessionAnswerRequest`.

Save:

```json
{
  "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
  "state": "answered",
  "answer_family": "rating",
  "answer_value": { "value": 8 }
}
```

Clear (same endpoint, immutable `cleared` revision — **no `DELETE` route**):

```json
{
  "client_mutation_id": "b10063cb-9fb4-4ac2-b399-769f8781127f",
  "state": "cleared"
}
```

The backend must follow the **exact** save ordering in
[admin-and-operations.md §27.3](admin-and-operations.md):

```text
1. Lock and validate the core session.
2. Update core last_activity_at.
3. Save the encrypted response revision.
4. Commit the response transaction.
5. Insert the core answer_saved analytics event.
6. Commit the core transaction.
7. Return success.
```

The **response write (step 4) is authoritative**; analytics (steps 5–6) are
secondary. A retry after a lost HTTP response is safe because of
`client_mutation_id` ([answer-flows.md §21](answer-flows.md)).

Returns `200 OK` for first saves, updates, and idempotent retries.

### 3.6 Record a question-view event

| Method | Path |
|---|---|
| `POST` | `/api/v1/public/submission-sessions/current/events/question-viewed` |

```json
{ "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539" }
```

Returns `204 No Content`. The backend validates the node belongs to the frozen
version and inserts a core analytics event. **Secondary metadata** — if the
insert fails, the respondent must still continue.

### 3.7 Complete the session

| Method | Path |
|---|---|
| `POST` | `/api/v1/public/submission-sessions/current/complete` |

No body. The backend locks the session, returns the existing completion if
already completed, validates the final canonical answer set, marks the session
`completed`, sets `completed_at`, inserts a `session_completed` event, and
rejects later edits.

Response (`CompleteSubmissionSessionResponses`):

```json
{ "status": "completed", "completed_at": "2026-06-11T01:31:00Z" }
```

Returns `200 OK` for both first and repeated completion — **idempotent**.

---

## 4. Frontend request sequences

Public slug entry:

```text
GET  /public/surveys/customer-intake
POST /public/submission-sessions
GET  /public/submission-sessions/current
PUT  /public/submission-sessions/current/answers/{question_node_id}
POST /public/submission-sessions/current/events/question-viewed
POST /public/submission-sessions/current/complete
```

Link-token entry:

```text
POST /public/links/resolve
POST /public/submission-sessions
GET  /public/submission-sessions/current
PUT  /public/submission-sessions/current/answers/{question_node_id}
POST /public/submission-sessions/current/events/question-viewed
POST /public/submission-sessions/current/complete
```

---

## 5. Endpoints to remove

The one-shot intake routes do not survive the migration. They currently accept
the entire answer list and immediately create a stored submission
([public.py](../../backend/app/api/v1/public.py)).

```text
POST /api/v1/public/submissions/slug    →  remove
POST /api/v1/public/submissions/link    →  remove
```

Replaced by `POST /submission-sessions` + `PUT .../answers/{question_node_id}`
+ `POST .../complete`. Follow a staged migration: add new routes, migrate the
React flow, stop calling the old routes, then remove them (or return `410 Gone`
during a deprecation window).

---

## 6. Optional endpoints (later)

| Endpoint | When it earns its place |
|---|---|
| `POST .../current/abandon` | Explicit "discard and exit" button. Otherwise the scheduled expiry task marks stale sessions abandoned ([implementation-order.md §38 Stage 5](implementation-order.md)). |
| `POST .../current/heartbeat` | Only if respondents linger on one page without saving or viewing. Answer saves and view events update `last_activity_at` often enough for v1. |
| `POST .../current/events` (batched) | Traffic reduction later. The explicit `question-viewed` route is easier to validate first. |

---

## 7. Implemented contract reference

The Pydantic models for the session routes **already exist** and this document
matches them:

| Concern | Model | File |
|---|---|---|
| Start request (union) | `StartSubmissionSessionRequest`, `SubmissionSessionAccess` | `requests/submission_sessions.py` |
| Save request | `SaveSubmissionSessionAnswerRequest` | `requests/submission_sessions.py` |
| View event request | `QuestionViewedEventRequest` | `requests/submission_sessions.py` |
| Session response | `PublicSubmissionSessionResponses` | `responses/submission_sessions.py` |
| Answer in response | `SubmissionSessionAnswerResponses` | `responses/submission_sessions.py` |
| Completion response | `CompleteSubmissionSessionResponses` | `responses/submission_sessions.py` |

> **Status enum.** `SubmissionSessionStatus` is
> `Literal["in_progress", "completed", "abandoned"]`, matching the
> `submission_sessions.session_status` CHECK constraint exactly. There is no
> `expired` status: expiry is enforced by comparing `expires_at` at read time
> and rejecting the request, not by a stored status value. A scheduled
> maintenance task transitions stale sessions to `abandoned`
> ([implementation-order.md §38 Stage 5](implementation-order.md)).
