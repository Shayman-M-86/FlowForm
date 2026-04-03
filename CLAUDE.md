# FlowForm — Claude Code Guide

## Project overview

FlowForm is a Flask backend for building and managing surveys. It uses **two separate PostgreSQL databases** — `core` and `response` — with strict separation of concerns between them.

## Layer architecture

Each layer has one job. When deciding where code belongs, follow this stack top to bottom:

```
schema/orm/       what the tables look like
db/               how you talk to the database
repositories/     reusable query helpers
services/         application behavior
schema/api/       what the API surface looks like
api/routes/       thin HTTP handlers
```

### `schema/orm/` — table definitions

Pure SQLAlchemy ORM models. Each class maps one table. No business logic, no cross-db relationships, no Pydantic. Split by database:

- `schema/orm/core/` — tables that live in the core DB
- `schema/orm/response/` — tables that live in the response DB

### `db/` — database plumbing

Engines, sessionmakers, declarative bases (`CoreBase`, `ResponseBase`), request-scoped session lifecycle, and transaction helpers (`commit_or_rollback`, `rollback_safely`). Nothing above this layer should import SQLAlchemy engine or connection objects directly.

### `repositories/` — query helpers *(not yet implemented)*

Reusable, DB-specific access patterns. A repository only talks to one database. It contains named query methods so that services stay readable and the same lookup is never written twice. Repositories do not coordinate across databases and do not contain workflow logic.

### `services/` — application behavior

The only layer that coordinates both databases. Services contain status transitions, cross-db saga workflows, pseudonymous identity handling, and anything that feels like a business decision. `SubmissionGateway` is the canonical example. Routes call services; services call repositories or ORM directly.

### `schema/api/` — API surface shapes

Pydantic models only. Split by direction:

- `schema/api/requests/` — validate incoming payloads before any business logic runs
- `schema/api/responses/` — define outgoing shapes; use `from_attributes=True` to map from ORM objects

These models never import from `schema/orm/`. The conversion happens in services or routes via `ResponseModel.model_validate(orm_obj)`.

### `api/routes/` — HTTP handlers *(thin)*

Parse the request, call a service, return a response. No SQL, no session management, no business logic. Routes are the glue between HTTP and services — nothing more.

---

## Running tests

```bash
bash "./backend/scripts/run-tests-rebuild-teardown.sh"
```

Filter with `-k`:
```bash
bash "./backend/scripts/run-tests-rebuild-teardown.sh" -k "test_submission_gateway"
```

Do not pass file paths to filter tests — use `-k` only.

---

## Two-database architecture

### core DB
Stores survey structure, projects, users, permissions, and submission metadata.

### response DB
Stores raw submission payloads and answer/event data in isolation. Can have its own backup, retention, and access policy.

### The link
There are **no cross-database foreign keys**. The application layer joins the two sides via a single shared integer:

```
core.survey_submissions.id  <->  response.submissions.core_submission_id
```

### Privacy and pseudonymity
The response DB must never store a real `user_id` for authenticated submissions. Instead:

1. A stable UUID is assigned once per `(user, project)` pair and stored in `core.response_subject_mappings`
2. That UUID (`pseudonymous_subject_id`) is what gets written into `response.submissions`

Reverse-identity lookup chain:
```
response.submission_answers
  -> response.submissions.pseudonymous_subject_id
  -> core.response_subject_mappings.user_id
  -> core.users
```

---

## Backend file structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py        # blueprint registration
│   │       └── health.py
│   ├── core/
│   │   ├── config.py              # Settings (Pydantic), get_settings()
│   │   ├── error.py               # Custom exceptions
│   │   ├── extensions.py          # db_manager singleton
│   │   ├── factory.py             # create_app() app factory
│   │   └── responses.py           # response envelope helpers
│   ├── db/
│   │   ├── base.py                # CoreBase, ResponseBase (DeclarativeBase)
│   │   ├── context.py             # get_core_db(), get_response_db() (Flask g)
│   │   ├── manager.py             # DatabaseManager — engines + sessionmakers
│   │   ├── session.py             # request lifecycle hooks
│   │   └── transaction.py        # commit_or_rollback(), rollback_safely()
│   ├── models/
│   │   ├── base.py                # TimestampMixin
│   │   ├── core/                  # SQLAlchemy models on CoreBase
│   │   │   ├── audit_log.py
│   │   │   ├── permission.py
│   │   │   ├── project.py         # Project, ProjectRole, ProjectMembership
│   │   │   ├── response_store.py  # ResponseStore
│   │   │   ├── response_subject_mapping.py  # pseudonymous UUID mapping
│   │   │   ├── survey.py          # Survey, SurveyVersion
│   │   │   ├── survey_access.py   # SurveyRole, SurveyPublicLink
│   │   │   ├── survey_content.py  # SurveyQuestion, SurveyRule, SurveyScoringRule
│   │   │   ├── survey_submission.py  # SurveySubmission (registry entry)
│   │   │   └── user.py
│   │   └── response/              # SQLAlchemy models on ResponseBase
│   │       ├── submission.py      # Submission (payload record)
│   │       ├── submission_answer.py
│   │       └── submission_event.py
│   ├── schemas/                   # (empty — target home for Pydantic API schemas)
│   │   # target layout:
│   │   # api/requests/   — Pydantic request models
│   │   # api/responses/  — Pydantic response models
│   └── services/
│       ├── linked_submission.py   # LinkedSubmission dataclass (domain object)
│       └── submission_gateway.py  # SubmissionGateway (cross-db coordinator)
└── tests/
    ├── integration/
    │   ├── conftest.py            # app, db_session, db_sessions, core/response connections
    │   ├── core/
    │   │   ├── conftest.py        # user, project, response_store, survey, survey_version fixtures
    │   │   ├── factories.py       # make_user(), make_project(), make_survey(), etc.
    │   │   ├── test_cross_db_submission_link.py  # low-level ORM linkage tests
    │   │   ├── test_submission_gateway.py        # SubmissionGateway integration tests
    │   │   └── test_*.py          # per-model tests
    │   ├── response/
    │   │   └── test_*.py
    │   └── environment/
    │       └── test_*.py
    └── unit/
        └── test_*.py

Schema/
    orm/ # The existing models folder could basically just be Put here.
    
```

---

## Key domain objects

### `SurveySubmission` (core DB)
Registry entry — holds channel, status, timestamps, `submitted_by_user_id`, `pseudonymous_subject_id`. Status lifecycle: `pending` → `stored` | `failed`.

### `Submission` (response DB)
Raw payload record — holds only `pseudonymous_subject_id` (never `user_id`), `core_submission_id`, and `metadata`.

### `ResponseSubjectMapping` (core DB)
Maps `(project_id, user_id)` → stable `pseudonymous_subject_id` UUID. Created once per user+project.

### `LinkedSubmission` (service layer)
App-level domain object wrapping both DB sides:
```python
@dataclass
class LinkedSubmission:
    core_submission: SurveySubmission
    response_submission: Submission
    subject_mapping: ResponseSubjectMapping | None
    user: User | None
    answers: list[SubmissionAnswer]
```

### `SubmissionGateway` (service layer)
Cross-db coordinator. Three methods:
- `get_or_create_subject_mapping(core_session, *, project_id, user_id)`
- `create_linked_submission(core_session, response_session, ...)` — saga workflow
- `load_linked_submission(core_session, response_session, *, core_submission_id, include_answers, resolve_identity)`

---

## Saga / submission write flow

```
1. get_or_create ResponseSubjectMapping in core
2. create SurveySubmission in core  (status='pending')
3. flush core → get the shared ID
4. create Submission in response DB (core_submission_id=...)
5. create SubmissionAnswer / SubmissionEvent rows
6. commit response DB
7. update core submission status → 'stored'
8. commit core DB
```

On response-side failure: rollback response, mark core `status='failed'`, commit core.

---

## Architecture rules

- ORM models are pure persistence models — no business logic, no cross-db relationships
- No cross-database SQLAlchemy relationship hacks
- `models/core/` uses `CoreBase`; `models/response/` uses `ResponseBase` — never mixed
- Pydantic schemas live in `schemas/` (separate from ORM models)
- Routes stay thin — cross-db orchestration belongs in `services/`
- `db/` is for engines, sessions, bases, and transaction helpers only
- `services/` is the orchestration layer — the only place that coordinates both DBs
- Response DB never receives a real `user_id`

---

## Test session fixtures (integration)

| Fixture | What it provides |
|---|---|
| `db_session` | Single session bound to both connections via `binds=` (legacy, for older tests) |
| `core_db_session` | Session bound to core connection only |
| `response_db_session` | Session bound to response connection only |
| `db_sessions` | `DbSessions(core=..., response=...)` namedtuple — use this for gateway/service tests |

All sessions use `join_transaction_mode="create_savepoint"` — commits release savepoints, outer transaction rolls back on teardown.
