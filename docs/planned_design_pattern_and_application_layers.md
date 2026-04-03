# Planned Design Pattern and Application Layers

## Overview

The application is divided into distinct layers. Each layer has a single responsibility and a clear boundary. Code should generally move downward through the stack: upper layers consume lower layers, never the other way around.

The core stack is:

```text
schema/api/         validation + serialization layer   (what the outside world sends and receives)
schema/orm/         data layer                         (what the database looks like)
repositories/       access layer                       (how you query a single DB/domain)
services/           logic layer                        (how business workflows run)
api/routes/         request layer                      (how HTTP maps to the above)
```

Alongside that stack, the application may also use:

```text
domain/             app-level concepts                 (what the application means by a "survey", "linked submission", etc.)
assemblers/         object construction helpers        (how related ORM results are combined into domain objects)
```

These do not replace the stack. They sit alongside it and support it.

---

## Layer Definitions

## 1. Data Layer — `schema/orm/`

The ORM models define exactly what is stored in the database. Each class maps to one table. Each field maps to one column. Nothing more.

This layer answers:

- what tables exist?
- what columns exist?
- how do rows map to Python objects?

This layer is about storage structure, not business workflows.

Examples:
- `SurveySubmission`
- `Submission`
- `ResponseSubjectMapping`

Rules:

- No business logic
- No Pydantic
- No cross-database relationships
- Purely descriptive — this is what the data looks like at rest

Split by database:

- `schema/orm/core/` — tables in the core database
- `schema/orm/response/` — tables in the response database

This preserves the fact that FlowForm uses two separate databases with different responsibilities, instead of pretending they are one unified relational graph.

---

## 2. Validation Layer — `schema/api/`

The API schema layer defines the boundary between the outside world and the application.

This layer answers:

- what request data do we accept?
- what response data do we return?

This layer is about validation and serialization, not business meaning.

Examples:
- `SubmissionCreate`
- `SubmissionRead`

Split by direction:

- `schema/api/requests/` — validates incoming payloads before any logic runs
- `schema/api/responses/` — shapes outgoing data before it leaves the application

Rules:

- No SQLAlchemy
- No database session access
- No business logic
- Request models validate input early and loudly
- Response models define the public output shape
- `from_attributes=True` on response models allows direct mapping from ORM-backed objects through `Model.model_validate(...)`

This layer exists so API contracts remain explicit and separate from both storage concerns and workflow logic.

---

## 3. Access Layer — `repositories/`

Repositories are named, reusable database access helpers built on top of the ORM and a session.

This layer answers:

- how do I fetch this ORM object?
- what repeated queries do I want to name?

This layer is about DB access, usually one database at a time.

Examples:
- load a survey by id
- load a user by email
- load a submission by `core_submission_id`

Rules:

- Each repository talks to one database only
- Each repository works with one closely related domain area
- Takes a session at construction time
- Does not manage its own sessions
- Returns ORM objects or `None`
- No business logic
- No cross-database coordination
- No HTTP concerns

What belongs here:

- `get_by_id`
- `get_by_email`
- `get_by_core_submission_id`
- repeated lookup/query patterns used in multiple places

Repositories keep raw query logic out of services and routes, but they do not own workflow behavior.

---

## 4. Logic Layer — `services/`

Services are the business workflow layer. They sit above repositories and ORM and define how the application behaves.

This layer answers:

- what business operation are we performing?
- what steps need to happen?
- what rules apply?
- what happens if part of the workflow fails?

This layer is about behavior and orchestration.

Examples:
- create a linked submission across core + response DB
- resolve pseudonymous identity
- move submission from `pending` to `stored`
- coordinate multi-step workflows

Rules:

- This is the only layer allowed to touch both databases at once
- Calls repositories for lookups where useful
- May use ORM directly for writes where needed
- Owns cross-database workflows and recovery logic
- No Flask `request`
- No `jsonify`
- No status code handling

What belongs here:

- Cross-database workflows
- Status transitions
- Pseudonymous identity resolution
- Business rules spanning more than one repository or model
- Application-coordinated transaction logic, including saga-style write flows when two databases must stay aligned

In FlowForm, this is the natural home for things like `SubmissionGateway` or `SubmissionService`.

---

## 5. Request Layer — `api/routes/`

Routes are thin HTTP handlers. They translate between HTTP and the service layer.

Their job is simple:

1. parse the request
2. validate it with a request schema
3. call one service method
4. serialize the result with a response schema
5. return the HTTP response

Rules:

- No SQL
- No session management
- No business logic
- No cross-database orchestration
- No persistence decisions

Pattern:

```python
@bp.post("/submissions")
def create_submission():
    payload = SubmissionCreate.model_validate(request.get_json() or {})
    result = submission_service.create(payload)
    return jsonify(SubmissionRead.model_validate(result).model_dump()), 201
```

Routes are glue, not logic.

---

## Domain Objects and Aggregates — `domain/`

Domain objects sit alongside the stack, not inside the storage or API layers.

A domain object is an application-level concept. It represents something meaningful to the app, not just a database row and not just a JSON shape.

Examples:
- `LinkedSubmission`
- `SurveyAggregate`
- `SubmissionStatus`

These are not API schemas and not ORM models. They are application-facing objects that make business logic easier to understand.

A domain object becomes an aggregate when it combines several related pieces into one conceptual unit.

Examples:

- `SurveyAggregate` may combine:
  - `Survey`
  - `SurveyVersion`
  - `SurveyContent`
  - related access or link information

- `LinkedSubmission` may combine:
  - core submission row
  - response submission row
  - subject mapping
  - answer rows
  - optional resolved user

Use a domain object or aggregate when the business logic naturally thinks in terms of one meaningful concept, even if that concept is backed by multiple ORM rows.

Do not use domain objects to mirror tables. That is what ORM models are for.

---

## Assemblers — `assemblers/` or local service helpers

An assembler is a builder. Its job is to take ORM objects or repository results and construct a domain object or aggregate.

Examples:
- `SurveyAssembler`
- `LinkedSubmissionAssembler`

Relationship to the rest of the stack:

- ORM = raw stored pieces
- repository = fetches pieces
- assembler = combines pieces
- service = decides when and why to do that

Assemblers are optional. A service may build an aggregate directly if the construction logic is small and local. A separate assembler is only useful when that composition logic becomes large, repeated, or worth naming clearly.

Assemblers should not contain business workflow rules. They construct objects; they do not decide the workflow.

---

## How the Layers Connect

A request flows top to bottom through the stack.

```text
HTTP request
    ↓
api/routes/             parses with schema/api/requests/
    ↓
services/               runs the use case and business workflow
    ↓
repositories/           loads/stores through ORM + session
    ↓
schema/orm/             maps to DB tables
    ↓
database
    ↓
schema/orm/             maps rows back to objects
    ↓
repositories/           returns ORM objects
    ↓
services/               applies rules and builds domain results
    ↓
api/routes/             serializes with schema/api/responses/
    ↓
HTTP response
```

Inside the service layer, the flow may also look like this:

```text
ORM rows / repository results
    ↓
domain object / aggregate
    ↓
response schema
```

That means services do not have to expose raw ORM rows as the thing the rest of the app thinks in. They can work with richer app-level concepts instead.

---

## Practical Differences Between the Layers

### API schema
For outside-in and inside-out data transfer.

### ORM
For database storage.

### Repository
For reusable DB queries and persistence helpers.

### Service
For business workflows, orchestration, and rules.

### Domain object / aggregate
For meaningful app-level concepts used by services.

### Assembler
For building those domain objects when the construction logic is non-trivial.

---

## What Goes Where — Quick Reference

| Situation | Layer |
|---|---|
| Defining a table column | `schema/orm/` |
| Validating an incoming JSON payload | `schema/api/requests/` |
| Shaping an outgoing API response | `schema/api/responses/` |
| Looking up a user by email | `repositories/` |
| Loading a survey and its related parts into one conceptual object | `services/` + optional `domain/` aggregate |
| Building a `SurveyAggregate` from multiple ORM results | service or `assemblers/` |
| Writing a submission to both databases | `services/` |
| Assigning a pseudonymous UUID | `services/` |
| Returning an HTTP 201 | `api/routes/` |
| Anything that touches two databases | `services/` only |

---

## Design Intent

This structure is meant to keep FlowForm understandable as it grows.

It protects against:

- business logic leaking into ORM models
- Pydantic models becoming persistence models
- repositories turning into workflow layers
- routes becoming large and stateful
- cross-database logic being scattered across the app
- application concepts being reduced to raw table rows

The goal is not abstraction for its own sake. The goal is clarity:

- the database layer describes storage
- the API layer describes contracts
- repositories describe access
- services describe behavior
- domain objects describe meaning