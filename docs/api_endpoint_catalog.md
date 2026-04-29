# FlowForm API v1 Reference

Canonical reference for the currently implemented Flask v1 API.

## Base URL

- API base: `/api/v1`
- Request content type: `application/json` for body-based endpoints
- Timestamp format: ISO-8601 datetime strings
- Versioning: path-based (`/api/v1`)
- Mounted prefixes:
  - `/api/v1/health`
  - `/api/v1/auth`
  - `/api/v1/public`
  - `/api/v1/projects`
- Health endpoints currently resolve under `/api/v1/health/health/...` because the health blueprint also defines its own `/health` prefix.
- `project_ref` accepts either a numeric project ID or a project slug.

## Authentication

- `require_auth`: endpoint requires an authenticated user.
- `optional_auth`: endpoint accepts both authenticated and unauthenticated callers.
- Public/no-auth: endpoint is available without authentication.

Current route behavior:

- `/api/v1/projects/...`: `require_auth`
- `POST /api/v1/auth/bootstrap-user`: `require_auth`
- `GET /api/v1/public/links/resolve`: `require_auth`
- `POST /api/v1/public/submissions/link`: `require_auth`
- `POST /api/v1/public/submissions/slug`: `optional_auth`
- `GET /api/v1/public/surveys` and `GET /api/v1/public/surveys/{public_slug}`: public/no-auth

## Errors

Errors use JSON responses. The lists under each endpoint are the most obvious/common failures, not an exhaustive catalog.

### AppError

Used for domain/service errors.

```json
{
  "code": "SURVEY_NOT_FOUND",
  "message": "Survey 22 was not found in project 9.",
  "details": {}
}
```

### Validation Error

Returned when request parsing or model validation fails.

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "errors": [
    {
      "field": "page_size",
      "message": "Input should be less than or equal to 100",
      "type": "less_than_equal"
    }
  ]
}
```

### HTTP Exception

Used for framework-level HTTP parsing or request-shape failures.

```json
{
  "code": "HTTP_415",
  "message": "Request body must be JSON"
}
```

### Auth Error

Used for authentication failures.

```json
{
  "code": "AUTHORIZATION_HEADER_MISSING",
  "message": "Authorization header is expected",
  "details": {}
}
```

### Internal Server Error

```json
{
  "code": "INTERNAL_SERVER_ERROR",
  "message": "An unexpected error occurred."
}
```

### Integrity Fallback

Unhandled database integrity errors are normalized to:

```json
{
  "code": "UNHANDLED_INTEGRITY_ERROR",
  "message": "A database integrity error occurred."
}
```

HTTP status: `409 Conflict`

## Shared Schemas

### Response Shapes

`ProjectOut`
- `id`
- `name`
- `slug`
- `created_by_user_id`
- `created_at`

`SurveyOut`
- `id`
- `project_id`
- `title`
- `visibility`
- `public_slug`
- `default_response_store_id`
- `published_version_id`
- `created_by_user_id`
- `created_at`
- `updated_at`

`SurveyVersionOut`
- `id`
- `survey_id`
- `version_number`
- `status`
- `compiled_schema`
- `published_at`
- `created_by_user_id`
- `created_at`
- `updated_at`

`NodeOut`
- `id`
- `survey_version_id`
- `node_key` (the stable content ID, e.g. `"q1"`, `"r1"`)
- `sort_key`
- `node_type` (`"question"` | `"rule"`)
- `content` (the full question or rule schema object)
- `created_at`
- `updated_at`

`ScoringRuleOut`
- `id`
- `survey_version_id`
- `scoring_key`
- `scoring_schema`
- `created_at`
- `updated_at`

`PublicLinkOut`
- `id`
- `survey_id`
- `token_prefix`
- `is_active`
- `assigned_email`
- `expires_at`
- `created_at`

`CoreSubmissionOut`
- `id`
- `project_id`
- `survey_id`
- `survey_version_id`
- `response_store_id`
- `submission_channel`
- `submitted_by_user_id`
- `survey_link_id`
- `submitter`
- `is_anonymous`
- `status`
- `started_at`
- `submitted_at`
- `created_at`

`SubmitterOut`
- `id`
- `email`
- `display_name`

`AnswerOut`
- `id`
- `question_key`
- `answer_family`
- `answer_value`
- `created_at`

`LinkedSubmissionOut`
- `core`: `CoreSubmissionOut`
- `answers`: `AnswerOut[]`

### Common Request Shapes

`CreateProjectRequest`
- `name: string`
- `slug: string`

`UpdateProjectRequest`
- `name?: string`
- `slug?: string`

`CreateSurveyRequest`
- `title: string`
- `visibility: "private" | "link_only" | "public"`
- `public_slug?: string`
- `default_response_store_id?: integer`

Rules:
- `public_slug` is required when `visibility = "public"`
- `public_slug` is forbidden unless `visibility = "public"`

`UpdateSurveyRequest`
- `title?: string`
- `visibility?: "private" | "link_only" | "public"`
- `public_slug?: string`
- `default_response_store_id?: integer`

`CreatePublicLinkRequest`
- `assigned_email?: string`
- `expires_at?: datetime`

`UpdatePublicLinkRequest`
- `is_active?: boolean`
- `assigned_email?: string`
- `expires_at?: datetime`

`SlugSubmissionRequest`
- `public_slug: string`
- `survey_version_id: integer`
- `started_at?: datetime`
- `submitted_at?: datetime`
- `answers: AnswerIn[]`
- `metadata?: object`

`LinkSubmissionRequest`
- `token: string`
- `survey_version_id: integer`
- `started_at?: datetime`
- `submitted_at?: datetime`
- `answers: AnswerIn[]`
- `metadata?: object`

`ListPublicSurveysRequest`
- `page?: integer`
- `page_size?: integer`

`ResolveTokenRequest`
- `token: string`

`ListSubmissionsRequest`
- `survey_id?: integer`
- `status?: "pending" | "stored" | "failed"`
- `submission_channel?: "link" | "slug" | "system"`
- `page?: integer`
- `page_size?: integer`

`GetSubmissionRequest`
- `include_answers?: boolean`
- `resolve_identity?: boolean`

### Minimal Polymorphic Payload Examples

Node payloads use `type` to discriminate between questions and rules. `sort_key` controls ordering across all nodes in a version. `content.id` must match the node's stable key and is used as `node_key` in responses.

Question node — `content` is discriminated by `content.family`:

```json
{
  "type": "question",
  "sort_key": 100000,
  "content": {
    "id": "email",
    "family": "field",
    "label": "Email address",
    "title": "Contact Info",
    "definition": {
      "variant": "email",
      "ui": { "placeholder": "you@example.com" }
    }
  }
}
```

Rule node — `content` uses an `if / then / else` structure:

```json
{
  "type": "rule",
  "sort_key": 500000,
  "content": {
    "id": "show_followup",
    "if": {
      "match": "ALL",
      "conditions": [
        {
          "target_id": "email",
          "family": "field",
          "requirements": { "type": "number", "operator": "GTE", "value": 18 }
        }
      ]
    },
    "then": {
      "set": [
        { "target_id": "followup", "visible": true, "required": true }
      ]
    },
    "else": {
      "do": { "skip_to": "end" }
    }
  }
}
```

Scoring payloads are discriminated by `scoring_schema.strategy`.

```json
{
  "scoring_key": "satisfaction_score",
  "scoring_schema": {
    "target": "satisfaction_rating",
    "bucket": "overall",
    "strategy": "rating_direct",
    "config": {
      "multiplier": 1
    }
  }
}
```

Answer payloads are discriminated by `answer_family`.

```json
{
  "question_key": "satisfaction_rating",
  "answer_family": "rating",
  "answer_value": {
    "value": 8
  }
}
```

## Endpoints

### Health

#### `GET /api/v1/health/health/`

- Purpose: simple liveness check.
- Auth: public/no-auth.
- Path/query params: none.
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Service is healthy", "data": { "timestamp": "<datetime>" } }`
- Obvious errors:
  - `500 INTERNAL_SERVER_ERROR`

#### `GET /api/v1/health/health/ready`

- Purpose: readiness check including database connectivity.
- Auth: public/no-auth.
- Path/query params: none.
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Service is ready", "data": { "timestamp": "<datetime>" } }`
  - `503 Service Unavailable`: `{ "message": "Database connectivity Failed: ...", "data": { "timestamp": "<datetime>" } }`
- Obvious errors:
  - `500 INTERNAL_SERVER_ERROR`

### Auth

#### `POST /api/v1/auth/bootstrap-user`

- Purpose: create or confirm the currently authenticated user in the local database.
- Auth: `require_auth`.
- Path/query params: none.
- Request shape:
  - `id_token: string`
- Success responses:
  - `200 OK`: `BootstrapUserOut`
  - `201 Created`: `BootstrapUserOut`
- Response shape:
  - `created: boolean`
  - `user: { id, auth0_user_id, email, display_name }`
- Obvious errors:
  - `401` auth required
  - `422 VALIDATION_ERROR`
  - `409 UNHANDLED_INTEGRITY_ERROR`

### Public

#### `GET /api/v1/public/surveys`

- Purpose: list publicly browsable surveys.
- Auth: public/no-auth.
- Path/query params:
  - `page?: integer`
  - `page_size?: integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `PaginatedPublicSurveysOut`
- Response shape:
  - `items: SurveyOut[]`
  - `total: integer`
  - `page: integer`
  - `page_size: integer`
- Obvious errors:
  - `422 VALIDATION_ERROR`

#### `GET /api/v1/public/surveys/{public_slug}`

- Purpose: fetch one public survey and its published version.
- Auth: public/no-auth.
- Path/query params:
  - `public_slug: string`
- Request shape: none.
- Success responses:
  - `200 OK`: `PublicSurveyOut`
- Response shape:
  - `survey: SurveyOut`
  - `published_version: SurveyVersionOut | null`
- Obvious errors:
  - `404` survey not found
  - `404` survey is not publicly accessible

#### `GET /api/v1/public/links/resolve`

- Purpose: resolve a link token to the survey and published version it grants access to.
- Auth: `require_auth`.
- Path/query params:
  - `token: string`
- Request shape: none.
- Success responses:
  - `200 OK`: `ResolveLinkOut`
- Response shape:
  - `link: PublicLinkOut`
  - `survey: SurveyOut`
  - `published_version: SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `403` link assigned to a different user/email
  - `404` token not found
  - `409` link inactive, expired, or survey unpublished
  - `422 VALIDATION_ERROR`

#### `POST /api/v1/public/submissions/slug`

- Purpose: create a submission for a public survey slug; authenticated callers are recorded, unauthenticated callers become anonymous submitters.
- Auth: `optional_auth`.
- Path/query params: none.
- Request shape:
  - `public_slug`
  - `survey_version_id`
  - `started_at?`
  - `submitted_at?`
  - `answers`
  - `metadata?`
- Minimal example:

```json
{
  "public_slug": "customer-intake",
  "survey_version_id": 3,
  "started_at": "2026-04-13T08:00:00Z",
  "submitted_at": "2026-04-13T08:01:00Z",
  "answers": [
    {
      "question_key": "satisfaction_rating",
      "answer_family": "rating",
      "answer_value": {
        "value": 8
      }
    }
  ],
  "metadata": {}
}
```

- Success responses:
  - `201 Created`: `LinkedSubmissionOut`
- Obvious errors:
  - `404` public survey not found
  - `409` survey version not publishable or does not match the public survey
  - `422 VALIDATION_ERROR`

#### `POST /api/v1/public/submissions/link`

- Purpose: create a submission using an authenticated survey link token.
- Auth: `require_auth`.
- Path/query params: none.
- Request shape:
  - `token`
  - `survey_version_id`
  - `started_at?`
  - `submitted_at?`
  - `answers`
  - `metadata?`
- Success responses:
  - `201 Created`: `LinkedSubmissionOut`
- Obvious errors:
  - `401` auth required
  - `403` link assigned to a different user/email
  - `404` token not found
  - `409` link inactive, expired, or survey unpublished
  - `422 VALIDATION_ERROR`

### Projects

#### `GET /api/v1/projects`

- Purpose: list projects visible to the authenticated actor.
- Auth: `require_auth`.
- Path/query params: none.
- Request shape: none.
- Success responses:
  - `200 OK`: `ProjectOut[]`
- Obvious errors:
  - `401` auth required

#### `POST /api/v1/projects`

- Purpose: create a project.
- Auth: `require_auth`.
- Path/query params: none.
- Request shape:
  - `name`
  - `slug`
- Success responses:
  - `201 Created`: `ProjectOut`
- Obvious errors:
  - `401` auth required
  - `409` duplicate slug
  - `422 VALIDATION_ERROR`

#### `GET /api/v1/projects/{project_ref}`

- Purpose: fetch one project by numeric ID or slug.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `ProjectOut`
- Obvious errors:
  - `401` auth required
  - `404` project not found
  - `403` access denied

#### `PATCH /api/v1/projects/{project_ref}`

- Purpose: partially update a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
- Request shape:
  - `name?`
  - `slug?`
- Success responses:
  - `200 OK`: `ProjectOut`
- Obvious errors:
  - `401` auth required
  - `404` project not found
  - `409` duplicate slug
  - `422 VALIDATION_ERROR`

#### `DELETE /api/v1/projects/{project_ref}`

- Purpose: delete a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Project deleted" }`
- Obvious errors:
  - `401` auth required
  - `404` project not found
  - `403` access denied

### Surveys

#### `GET /api/v1/projects/{project_ref}/surveys`

- Purpose: list surveys in a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyOut[]`
- Obvious errors:
  - `401` auth required
  - `404` project not found

#### `POST /api/v1/projects/{project_ref}/surveys`

- Purpose: create a survey in a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
- Request shape:
  - `title`
  - `visibility`
  - `public_slug?`
  - `default_response_store_id?`
- Success responses:
  - `201 Created`: `SurveyOut`
- Obvious errors:
  - `401` auth required
  - `404` project not found
  - `409` duplicate public slug or invalid survey state
  - `422 VALIDATION_ERROR`

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}`

- Purpose: fetch one survey in a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
  - `survey_id: integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyOut`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found

#### `PATCH /api/v1/projects/{project_ref}/surveys/{survey_id}`

- Purpose: partially update a survey.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
  - `survey_id: integer`
- Request shape:
  - `title?`
  - `visibility?`
  - `public_slug?`
  - `default_response_store_id?`
- Success responses:
  - `200 OK`: `SurveyOut`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found
  - `409` duplicate public slug or invalid state transition
  - `422 VALIDATION_ERROR`

#### `DELETE /api/v1/projects/{project_ref}/surveys/{survey_id}`

- Purpose: delete a survey.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref: string | integer`
  - `survey_id: integer`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Survey deleted" }`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found

### Versions

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/versions`

- Purpose: list survey versions.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyVersionOut[]`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions`

- Purpose: create a new survey version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
- Request shape: none.
- Success responses:
  - `201 Created`: `SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found
  - `409` version lifecycle conflict

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}`

- Purpose: fetch one survey version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/copy-to-draft`

- Purpose: copy an existing version into a new draft version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `201 Created`: `SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found
  - `409` version lifecycle conflict

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/publish`

- Purpose: publish a version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found
  - `409` invalid publish transition

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/archive`

- Purpose: archive a version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `200 OK`: `SurveyVersionOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found
  - `409` invalid archive transition

### Content

Questions and rules are unified as **nodes**, ordered by `sort_key`. Both are stored in the same table and returned by the same endpoints, discriminated by `node_type`.

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/nodes`

- Purpose: list all nodes (questions and rules) for a survey version, ordered by `sort_key`.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `200 OK`: `NodeOut[]`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/nodes`

- Purpose: create a node (question or rule) in a survey version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape:
  - `type: "question" | "rule"`
  - `sort_key: integer > 0`
  - `content: QuestionContentIn | RuleContentIn` (discriminated by `type`)
- Success responses:
  - `201 Created`: `NodeOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found
  - `409` duplicate node key, duplicate sort_key, or non-draft version
  - `422 VALIDATION_ERROR`

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`

- Purpose: fetch one node by ID.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
  - `node_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `NodeOut`
- Obvious errors:
  - `401` auth required
  - `404` node or parent resources not found

#### `PATCH /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`

- Purpose: partially update a node. `type` cannot be changed after creation.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
  - `node_id`
- Request shape:
  - `sort_key?: integer > 0`
  - `content?: QuestionContentIn | RuleContentIn`
- Success responses:
  - `200 OK`: `NodeOut`
- Obvious errors:
  - `401` auth required
  - `404` node or parent resources not found
  - `409` duplicate sort_key or non-draft version
  - `422 VALIDATION_ERROR`

#### `DELETE /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`

- Purpose: delete a node.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
  - `node_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Node deleted" }`
- Obvious errors:
  - `401` auth required
  - `404` node or parent resources not found
  - `409` non-draft version

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/scoring-rules`

- Purpose: list scoring rules for a survey version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape: none.
- Success responses:
  - `200 OK`: `ScoringRuleOut[]`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/scoring-rules`

- Purpose: create a scoring rule for a survey version.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
- Request shape:
  - `scoring_key`
  - `scoring_schema`
- Success responses:
  - `201 Created`: `ScoringRuleOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or version not found
  - `409` duplicate scoring key or non-draft version
  - `422 VALIDATION_ERROR`

#### `PATCH /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/scoring-rules/{scoring_rule_id}`

- Purpose: partially update a scoring rule.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
  - `scoring_rule_id`
- Request shape:
  - `scoring_key?`
  - `scoring_schema?`
- Success responses:
  - `200 OK`: `ScoringRuleOut`
- Obvious errors:
  - `401` auth required
  - `404` scoring rule or parent resources not found
  - `409` duplicate key or non-draft version
  - `422 VALIDATION_ERROR`

#### `DELETE /api/v1/projects/{project_ref}/surveys/{survey_id}/versions/{version_number}/scoring-rules/{scoring_rule_id}`

- Purpose: delete a scoring rule.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `version_number`
  - `scoring_rule_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Scoring rule deleted" }`
- Obvious errors:
  - `401` auth required
  - `404` scoring rule or parent resources not found
  - `409` non-draft version

### Links

#### `GET /api/v1/projects/{project_ref}/surveys/{survey_id}/links`

- Purpose: list links for a survey.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "links": PublicLinkOut[] }`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found

#### `POST /api/v1/projects/{project_ref}/surveys/{survey_id}/links`

- Purpose: create a link for a survey.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
- Request shape:
  - `assigned_email?`
  - `expires_at?`
- Success responses:
  - `201 Created`: `CreatePublicLinkOut`
- Response shape:
  - `link: PublicLinkOut`
  - `token: string`
  - `url: string`
- Obvious errors:
  - `401` auth required
  - `404` project or survey not found
  - `409` invalid visibility/link assignment combination
  - `422 VALIDATION_ERROR`

#### `PATCH /api/v1/projects/{project_ref}/surveys/{survey_id}/links/{link_id}`

- Purpose: partially update a link.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `link_id`
- Request shape:
  - `is_active?`
  - `assigned_email?`
  - `expires_at?`
- Success responses:
  - `200 OK`: `PublicLinkOut`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or link not found
  - `409` invalid visibility/link assignment combination
  - `422 VALIDATION_ERROR`

#### `DELETE /api/v1/projects/{project_ref}/surveys/{survey_id}/links/{link_id}`

- Purpose: delete a link.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id`
  - `link_id`
- Request shape: none.
- Success responses:
  - `200 OK`: `{ "message": "Link deleted" }`
- Obvious errors:
  - `401` auth required
  - `404` project, survey, or link not found

### Submissions

#### `GET /api/v1/projects/{project_ref}/submissions`

- Purpose: list submissions for a project.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `survey_id?`
  - `status?`
  - `submission_channel?`
  - `page?`
  - `page_size?`
- Request shape: none.
- Success responses:
  - `200 OK`: `PaginatedSubmissionsOut`
- Response shape:
  - `items: CoreSubmissionOut[]`
  - `total: integer`
  - `page: integer`
  - `page_size: integer`
- Obvious errors:
  - `401` auth required
  - `404` project not found
  - `422 VALIDATION_ERROR`

#### `GET /api/v1/projects/{project_ref}/submissions/{submission_id}`

- Purpose: fetch one submission and its stored answers.
- Auth: `require_auth`.
- Path/query params:
  - `project_ref`
  - `submission_id`
  - `include_answers?: boolean`
  - `resolve_identity?: boolean`
- Request shape: none.
- Success responses:
  - `200 OK`: `LinkedSubmissionOut`
- Obvious errors:
  - `401` auth required
  - `404` project or submission not found
  - `403` access denied
  - `422 VALIDATION_ERROR`
