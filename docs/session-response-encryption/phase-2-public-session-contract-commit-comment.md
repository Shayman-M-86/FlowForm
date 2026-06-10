# Phase 2 Public Session Contract Commit Comment

Generated from the current public session API contract work on 2026-06-11.

## Proposed Commit Subject

```text
api: add public submission session contract routes
```

## Proposed Commit Body

This commit starts Phase 2 by adding the public respondent session API
contract beside the legacy one-shot submission flow. The goal is not to adapt
the old plaintext submission service. The goal is to lock the new request and
response surface that later services will implement over `SubmissionSession`,
`ResponseEnvelope`, `ResponseAnswer`, and `ResponseAnswerRevision`.

The new contract follows `docs/session-response-encryption/api-structure.md`:
respondents address their active browser session as `current`, not by a public
`session_id`; link tokens are submitted in a JSON body rather than a query
string; answers are saved one question at a time by `question_node_id`; and
completion is an idempotent session operation.

The route behavior is intentionally skeletal. Public session routes validate
the final request shapes, return stable placeholder response bodies, and set
the planned HttpOnly resume cookie name. Real cross-database orchestration,
token hashing/storage, encrypted answer writes, analytics events, and lifecycle
rules remain Phase 3 through Phase 5 work.

## What Changed

### Public Session Routes

Added the five public respondent session endpoints in
`backend/app/api/v1/public.py`:

- `POST /api/v1/public/submission-sessions`
- `GET /api/v1/public/submission-sessions/current`
- `PUT /api/v1/public/submission-sessions/current/answers/{question_node_id}`
- `POST /api/v1/public/submission-sessions/current/events/question-viewed`
- `POST /api/v1/public/submission-sessions/current/complete`

These routes are contract stubs. They do not call the old
`SubmissionIntakeService`, and they do not write to either database yet.

### Link Resolution Transport

Changed public link resolution to match the API structure document:

- from `GET /api/v1/public/links/resolve?token=...`
- to `POST /api/v1/public/links/resolve`

The endpoint now parses `ResolveTokenRequest` from the JSON request body. This
keeps raw link tokens out of query strings, browser history, copied URLs, and
common request logs. The endpoint remains a preview operation only; starting a
submission session must revalidate access later.

### Public Session Request Schemas

Added `backend/app/schema/api/requests/submission_sessions.py`.

The start-session request uses a discriminated `access` union:

- `{"type": "public_slug", "public_slug": "..."}`
- `{"type": "link_token", "token": "..."}`

This deliberately replaces the old split between slug and link submission
routes and leaves room for later access channels without creating another
session-start endpoint.

The answer-save request now accepts:

- `client_mutation_id`
- `state`
- `answer_family`
- `answer_value`

It rejects body-level `question_node_id`. The question UUID belongs only in the
route path so clients do not send competing identifiers.

The clear-answer request is the same endpoint with `state: "cleared"` and no
answer payload. That preserves the planned immutable revision model: clearing
an answer becomes another revision, not a delete route.

### Public Session Response Schemas

Added `backend/app/schema/api/responses/submission_sessions.py`.

The public session response exposes only respondent-safe state:

- session status
- server-owned lifecycle timestamps
- survey summary
- frozen published version shape
- canonical latest answers

It does not expose the raw browser resume token, response envelope id,
locators, wrapped DEK, KMS key information, ciphertext, or nonce values.

### Temporary Placeholder Helpers

Added `backend/app/api/v1/public_submission_session_temp.py`.

This helper module keeps the temporary Phase 2 scaffolding out of the main
route file:

- `build_placeholder_session_response()` creates the stable placeholder body
  used before real session lookup and answer hydration exist.
- `set_placeholder_submission_session_cookie()` reserves the planned
  `flowform_submission_session` cookie name and security attributes.

The docstrings explicitly call out that the placeholder cookie value is not
authentication and must not become persisted state.

### Legacy Endpoint Markers

The old one-shot plaintext submission endpoints are still present for now:

- `POST /api/v1/public/submissions/slug`
- `POST /api/v1/public/submissions/link`

They are marked in `public.py` with decommission TODOs. This records the
decision to keep them temporarily while the frontend and service layers move to
the session API, rather than silently pretending they are part of the new
model.

### Contract Tests

Added `backend/tests/unit/test_submission_session_contracts.py`.

The tests pin the contract choices that are easiest to accidentally regress:

- start-session accepts `public_slug` access;
- legacy one-shot fields such as `survey_version_id`, `started_at`,
  `submitted_at`, `answers`, and `metadata` are rejected;
- answer saves reject body-level `question_node_id`;
- answered saves require answer payload fields;
- cleared saves reject answer payload fields;
- the OpenAPI spec exposes the expected Phase 2 public paths and methods;
- `links/resolve` is POST-only in the generated spec.

## Checklist Comparison

The public half of Phase 2 is now checked off in
`docs/session-response-encryption/implementation-checklist.md`.

Completed:

- Public session route stubs exist.
- Public start/current/save/event/complete request and response schemas exist.
- Link resolution now follows the body-based POST structure from
  `api-structure.md`.
- Public session routes validate request shapes.
- Public session routes return stable placeholder responses where real service
  behavior is not implemented yet.
- OpenAPI generation still works for the new route set.
- Legacy one-shot submission routes have an explicit temporary/decommission
  decision recorded next to the endpoints.

Still open:

- Administrator response routes are not implemented.
- Admin list/detail/history/export/delete schemas are not implemented.
- Real session services are not implemented.
- Real answer revision persistence is not implemented.
- Completion/lifecycle enforcement is not implemented.
- Frontend integration has not moved from one-shot final submit to incremental
  session saves.

The Phase 2 `Done when` route/placeholder checklist remains partially open
because the administrator response API is still missing.

## Why This Is Being Done Now

Phase 1 gave the database a new shape. Phase 2 gives clients and OpenAPI a new
contract to target before service behavior is wired in.

That split matters because the legacy public submission routes encode the old
world:

- create a submission once;
- send every answer in one payload;
- trust browser-supplied lifecycle timestamps/version ids;
- write plaintext answer values through the old response path.

The new public contract encodes the replacement model:

- start or resume a browser session;
- freeze access and version on the backend;
- save answers incrementally;
- treat retries through `client_mutation_id`;
- record analytics as secondary events;
- complete the session idempotently.

Putting this contract in place now gives the upcoming service layer a stable
target without dragging the old intake service forward.

## Current Risk And Expected Breakage

- The new session endpoints are placeholders. They validate shape and return
  stable contract responses, but they do not yet create sessions, envelopes, or
  answer revisions.
- The placeholder cookie value is intentionally fake. It reserves the cookie
  contract only.
- The old one-shot submission endpoints still exist and still call the legacy
  submission intake service.
- Public link resolution has changed from GET/query to POST/body. Any caller
  still using `GET /links/resolve?token=...` must be updated.
- Admin response routes are still absent, so Studio results should not be moved
  to the new response API yet.

## Validation Notes

Focused validation run during this work:

```text
uv run ruff check app/api/v1/public.py app/api/v1/public_submission_session_temp.py app/schema/api/requests/submission_sessions.py app/schema/api/responses/submission_sessions.py tests/unit/test_submission_session_contracts.py
```

Result:

```text
All checks passed.
```

Focused unit/OpenAPI validation:

```text
uv run pytest tests/unit/test_submission_session_contracts.py tests/unit/test_openapi_spec.py tests/unit/test_public_link_validation.py -q
```

Result:

```text
34 passed
```

Minimal OpenAPI smoke confirmed:

```text
/api/v1/public/surveys                                             GET
/api/v1/public/surveys/{public_slug}                               GET
/api/v1/public/links/resolve                                       POST
/api/v1/public/submission-sessions                                 POST
/api/v1/public/submission-sessions/current                         GET
/api/v1/public/submission-sessions/current/answers/{question_node_id} PUT
/api/v1/public/submission-sessions/current/events/question-viewed   POST
/api/v1/public/submission-sessions/current/complete                 POST
```

## Files Touched By This Phase

API routes:

- `backend/app/api/v1/public.py`
- `backend/app/api/v1/public_submission_session_temp.py`

API schemas:

- `backend/app/schema/api/requests/submission_sessions.py`
- `backend/app/schema/api/responses/submission_sessions.py`

Tests:

- `backend/tests/unit/test_submission_session_contracts.py`

Docs:

- `docs/session-response-encryption/api-structure.md`
- `docs/session-response-encryption/implementation-checklist.md`
- `docs/session-response-encryption/phase-2-public-session-contract-commit-comment.md`

## Suggested Next Commit

Continue Phase 2 with the administrator response contract, but keep it
contract-only:

- `GET /projects/{project_id}/surveys/{survey_id}/responses`
- `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`
- `GET /projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history`
- `POST /projects/{project_id}/surveys/{survey_id}/responses/export`
- `DELETE /projects/{project_id}/surveys/{survey_id}/responses/{session_id}`

Those routes should be survey-scoped, should not reuse integer legacy
submission ids, and should keep history/export/delete permissions explicit.
