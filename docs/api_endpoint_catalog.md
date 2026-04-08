# FlowForm API v1 Reference

This is the canonical API reference for the currently implemented Flask v1 endpoints.

## 1) Base URL, Versioning, and Content Type

- **API base:** `/api/v1`
- **Versioning:** URL versioning (`/v1`)
- **Content type for request bodies:** `application/json`
- **Timestamp format:** ISO-8601 datetime strings (examples in this document use UTC `Z`).

### Blueprint-to-prefix mapping

`register_api_v1()` mounts each blueprint using:

- `/api/v1/health`
- `/api/v1/projects`
- `/api/v1/public`

> Note: `health_v1` also has its own internal blueprint prefix (`/health`), so health endpoints are available under `/api/v1/health/health/...`.

---

## 2) Authentication and Authorization

- There is **no explicit auth middleware documented at the route layer** in these v1 handlers.
- Endpoints under `/projects` should be treated as **authenticated/owner/admin APIs** by client convention.
- Endpoints under `/public` are intended for public survey access and submissions.

---

## 3) Common Validation and Error Behavior

### Request parsing behavior

- JSON body endpoints require:
  - `Content-Type: application/json`
  - Body must be a **JSON object** (not an array/string/etc.)
- Query-based endpoints parse query strings into typed Pydantic models.

### Error shapes

### A) Domain/application error

```json
{
  "code": "SURVEY_NOT_FOUND",
  "message": "Survey 22 was not found in project 9.",
  "details": {}
}
```

### B) Validation error (`422`)

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

### C) HTTP parsing/media error (`4xx`)

```json
{
  "code": "HTTP_415",
  "message": "Request body must be JSON"
}
```

### D) Unhandled server error (`500`)

```json
{
  "code": "INTERNAL_SERVER_ERROR",
  "message": "An unexpected error occurred."
}
```

---

## 4) Shared Schema Components

## 4.1 Survey

### `CreateSurveyRequest`

```json
{
  "title": "Customer Intake",
  "visibility": "public",
  "allow_public_responses": true,
  "public_slug": "customer-intake",
  "default_response_store_id": 3
}
```

Rules:

- `visibility`: `private | link_only | public`
- `public_slug` is required when `visibility = public`
- `allow_public_responses` requires `visibility` in `link_only | public`

### `UpdateSurveyRequest`

All fields optional:

```json
{
  "title": "Customer Intake v2",
  "visibility": "link_only",
  "allow_public_responses": true,
  "public_slug": "customer-intake-v2",
  "default_response_store_id": 5
}
```

### `SurveyOut` (response)

Fields: `id`, `project_id`, `title`, `visibility`, `allow_public_responses`, `public_slug`, `default_response_store_id`, `published_version_id`, `created_by_user_id`, `created_at`, `updated_at`.

## 4.2 Versions

### `SurveyVersionOut`

Fields: `id`, `survey_id`, `version_number`, `status`, `compiled_schema`, `published_at`, `created_by_user_id`, `created_at`, `updated_at`.

## 4.3 Content (Questions / Rules / Scoring Rules)

### Create/Update question

```json
{
  "question_key": "q_age",
  "question_schema": {
    "type": "number",
    "label": "How old are you?",
    "required": true
  }
}
```

Update allows either field to be omitted.

### Create/Update rule

```json
{
  "rule_key": "eligibility_check",
  "rule_schema": {
    "if": {"question_key": "q_age", "op": "lt", "value": 18},
    "then": {"action": "end_survey"}
  }
}
```

### Create/Update scoring rule

```json
{
  "scoring_key": "risk_score",
  "scoring_schema": {
    "weights": {"q1": 10, "q2": 5}
  }
}
```

## 4.4 Public Links

### `CreatePublicLinkRequest`

```json
{
  "allow_response": true,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### `UpdatePublicLinkRequest`

```json
{
  "is_active": true,
  "allow_response": true,
  "expires_at": "2027-01-31T23:59:59Z"
}
```

### `CreatePublicLinkOut`

```json
{
  "link": {
    "id": 44,
    "survey_id": 11,
    "token_prefix": "a1b2c3",
    "is_active": true,
    "allow_response": true,
    "expires_at": null,
    "created_at": "2026-04-07T15:10:00Z"
  },
  "token": "<plaintext-token-returned-once>",
  "url": "https://your-host/api/v1/public/links/resolve?token=<token>"
}
```

## 4.5 Submissions

### `AnswerIn`

```json
{
  "question_key": "q_age",
  "answer_family": "number",
  "answer_value": {"value": 34}
}
```

### `CreateSubmissionRequest`

```json
{
  "survey_version_id": 7,
  "submitted_by_user_id": 101,
  "is_anonymous": false,
  "started_at": "2026-04-07T14:01:00Z",
  "submitted_at": "2026-04-07T14:03:30Z",
  "answers": [
    {
      "question_key": "q_age",
      "answer_family": "number",
      "answer_value": {"value": 34}
    }
  ],
  "metadata": {
    "source": "web-app"
  }
}
```

### `PublicSubmissionRequest`

```json
{
  "public_token": "<plaintext-token>",
  "survey_version_id": 7,
  "is_anonymous": true,
  "answers": [
    {
      "question_key": "q_age",
      "answer_family": "number",
      "answer_value": {"value": 34}
    }
  ],
  "metadata": {
    "utm_campaign": "spring_launch"
  },
  "started_at": "2026-04-07T14:01:00Z",
  "submitted_at": "2026-04-07T14:03:30Z"
}
```

### `ListSubmissionsRequest` (query params)

| Name | Type | Required | Notes |
|---|---|---|---|
| `survey_id` | int | No | Optional filter |
| `status` | string | No | Optional filter |
| `submission_channel` | string | No | Optional filter |
| `page` | int | No | Default `1`, min `1` |
| `page_size` | int | No | Default `20`, min `1`, max `100` |

### `GetSubmissionRequest` (query params)

| Name | Type | Required | Notes |
|---|---|---|---|
| `include_answers` | bool | No | Default `false` |
| `resolve_identity` | bool | No | Default `false` |

### `PaginatedSubmissionsOut`

```json
{
  "items": [
    {
      "id": 1,
      "project_id": 9,
      "survey_id": 11,
      "survey_version_id": 7,
      "response_store_id": 3,
      "submission_channel": "authenticated",
      "submitted_by_user_id": 101,
      "public_link_id": null,
      "is_anonymous": false,
      "status": "submitted",
      "started_at": "2026-04-07T14:01:00Z",
      "submitted_at": "2026-04-07T14:03:30Z",
      "created_at": "2026-04-07T14:03:31Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## 5) Endpoint Reference

## 5.1 Health

| Method | Path | Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/health/health/` | None | None | No |
| GET | `/api/v1/health/health/ready` | None | None | No |
| GET | `/api/v1/health/health/db` | None | None | No |

### Example

```bash
curl -X GET http://localhost:5000/api/v1/health/health/db
```

---

## 5.2 Projects: Surveys

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys` | `CreateSurveyRequest` | None | No |
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>` | None | None | No |
| PATCH | `/api/v1/projects/<project_id>/surveys/<survey_id>` | `UpdateSurveyRequest` | None | No |
| DELETE | `/api/v1/projects/<project_id>/surveys/<survey_id>` | None | None | No |

### Example (create survey)

```bash
curl -X POST http://localhost:5000/api/v1/projects/9/surveys \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Customer Intake",
    "visibility":"public",
    "allow_public_responses":true,
    "public_slug":"customer-intake"
  }'
```

---

## 5.3 Projects: Versions

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions` | None | None | No |
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/publish` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/archive` | None | None | No |

---

## 5.4 Projects: Questions

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/questions` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/questions` | `CreateQuestionRequest` | None | No |
| PATCH | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/questions/<question_id>` | `UpdateQuestionRequest` | None | No |
| DELETE | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/questions/<question_id>` | None | None | No |

---

## 5.5 Projects: Rules

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/rules` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/rules` | `CreateRuleRequest` | None | No |
| PATCH | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/rules/<rule_id>` | `UpdateRuleRequest` | None | No |
| DELETE | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/rules/<rule_id>` | None | None | No |

---

## 5.6 Projects: Scoring Rules

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/scoring-rules` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/scoring-rules` | `CreateScoringRuleRequest` | None | No |
| PATCH | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/scoring-rules/<scoring_rule_id>` | `UpdateScoringRuleRequest` | None | No |
| DELETE | `/api/v1/projects/<project_id>/surveys/<survey_id>/versions/<version_id>/scoring-rules/<scoring_rule_id>` | None | None | No |

---

## 5.7 Projects: Public Link Management

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/projects/<project_id>/surveys/<survey_id>/public-links` | None | None | No |
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/public-links` | `CreatePublicLinkRequest` | None | No |
| PATCH | `/api/v1/projects/<project_id>/surveys/<survey_id>/public-links/<link_id>` | `UpdatePublicLinkRequest` | None | No |
| DELETE | `/api/v1/projects/<project_id>/surveys/<survey_id>/public-links/<link_id>` | None | None | No |

### Example (create link)

```bash
curl -X POST http://localhost:5000/api/v1/projects/9/surveys/11/public-links \
  -H "Content-Type: application/json" \
  -d '{
    "allow_response": true,
    "expires_at": "2026-12-31T23:59:59Z"
  }'
```

---

## 5.8 Projects: Submissions (Authenticated)

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| POST | `/api/v1/projects/<project_id>/surveys/<survey_id>/submissions` | `CreateSubmissionRequest` | None | No |
| GET | `/api/v1/projects/<project_id>/submissions` | None | `ListSubmissionsRequest` | **Yes** |
| GET | `/api/v1/projects/<project_id>/submissions/<submission_id>` | None | `GetSubmissionRequest` | No |

### Pagination details

- Pagination applies only to `GET /api/v1/projects/<project_id>/submissions`.
- Uses `page` and `page_size` query parameters.
- Response includes `items`, `total`, `page`, and `page_size`.
- Optional `status` filter values: `pending`, `stored`, `failed`.

### Example (list submissions)

```bash
curl -G http://localhost:5000/api/v1/projects/9/submissions \
  --data-urlencode "survey_id=11" \
  --data-urlencode "status=stored" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=20"
```

---

## 5.9 Public Endpoints

| Method | Path | Request Body | Query | Pagination |
|---|---|---|---|---|
| GET | `/api/v1/public/surveys/<public_slug>` | None | None | No |
| GET | `/api/v1/public/links/resolve` | Optional JSON body (`{"token":"..."}`) or query `token` | `token` | No |
| POST | `/api/v1/public/submissions` | `PublicSubmissionRequest` | None | No |

### Example (resolve token via query)

```bash
curl -G http://localhost:5000/api/v1/public/links/resolve \
  --data-urlencode "token=<plaintext-token>"
```

### Example (public submission)

```bash
curl -X POST http://localhost:5000/api/v1/public/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "public_token":"<plaintext-token>",
    "survey_version_id":7,
    "is_anonymous":true,
    "answers":[
      {
        "question_key":"q_age",
        "answer_family":"number",
        "answer_value":{"value":34}
      }
    ]
  }'
```

---

## 6) Quick Route Count

- Health routes: 3
- Project routes: 29
- Public routes: 3
- **Total**: 35
