# Planned Design Pattern and Application Layers

## 1. Purpose

This document defines the intended application structure for FlowForm.

Its purpose is to:
- define clear boundaries between layers
- keep storage, validation, business logic, and HTTP concerns separate
- make the two-database architecture explicit
- support app-level concepts without coupling them to raw ORM models or API schemas
- reduce ambiguity about where new code should live

This is a design specification, not a discussion document.

---

## 2. Architectural Principles

### 2.1 Separation of concerns
Each layer has one primary responsibility.

### 2.2 Direction of dependency
Dependencies flow downward.
Upper layers may consume lower layers.
Lower layers must not depend on upper layers.

### 2.3 Explicit two-database architecture
The core database and response database remain explicit in the design.
The system must not pretend they are one relational model.

### 2.4 No cross-database ORM relationships
Cross-database linking belongs in application logic, not in SQLAlchemy relationship configuration.

### 2.5 Application concepts are not storage models
If the application needs a meaningful object composed from multiple ORM rows, that object belongs in the domain layer, not in `schema/orm/`.

### 2.6 API contracts are not persistence models
Pydantic models define external input and output shapes.
They do not define database storage and do not own business logic.

---

## 3. Layer Stack

```text
schema/api/         validation + serialization layer   (what the outside world sends and receives)
schema/orm/         data layer                         (what the database looks like)
repositories/       access layer                       (how a single DB/domain is queried)
services/           logic layer                        (how business workflows run)
api/routes/         request layer                      (how HTTP maps to the above)
```

Alongside that stack:

```text
domain/             app-level concepts                 (meaningful application objects)
assemblers/         construction helpers               (optional builders for domain objects)
```

These supporting areas do not replace the stack.
They support the service layer and help express business meaning clearly.

---

## 4. Layer Definitions

## 4.1 `schema/orm/` — Data Layer

### Responsibility
Defines how data is stored.

### This layer answers
- what tables exist
- what columns exist
- how rows map to Python objects

### Contains
- SQLAlchemy ORM models
- table mappings
- column definitions
- single-database relationships where valid

### Does not contain
- business logic
- Pydantic models
- HTTP concerns
- cross-database relationships
- workflow coordination

### Database split
- `schema/orm/core/` — core database models
- `schema/orm/response/` — response database models

### Examples
- `SurveySubmission`
- `Submission`
- `ResponseSubjectMapping`

### Rule
ORM models are storage definitions only.
They describe data at rest.

---

## 4.2 `schema/api/` — Validation and Serialization Layer

### Responsibility
Defines how data enters and leaves the application.

### This layer answers
- what request data is accepted
- what response data is returned

### Contains
- Pydantic request models
- Pydantic response models
- validation rules for API payloads
- serialization output shapes

### Split by direction
- `schema/api/requests/` — incoming payload validation
- `schema/api/responses/` — outgoing response shaping

### Does not contain
- SQLAlchemy models
- database session access
- repository logic
- workflow logic
- HTTP response construction

### Examples
- `SubmissionCreate`
- `SubmissionRead`

### Rule
API schemas are contract models.
They are not domain objects and not persistence models.

### Note
Response models may use `from_attributes=True` to map from ORM-backed or domain-backed objects via `model_validate(...)`.

---

## 4.3 `repositories/` — Access Layer

### Responsibility
Provides reusable, named database access operations.

### This layer answers
- how do I fetch this ORM object
- what repeated query patterns should be named

### Contains
- reusable lookup methods
- repeated query helpers
- single-database persistence access patterns

### Does not contain
- business logic
- cross-database coordination
- session lifecycle management
- HTTP concerns
- workflow decisions

### Constraints
- each repository talks to one database only
- each repository should stay scoped to one closely related domain area
- repositories receive a session; they do not create or manage one
- repositories return ORM objects, collections, or `None`

### Examples
- `get_by_id`
- `get_by_email`
- `get_by_core_submission_id`

### Rule
Repositories are for access patterns, not business behavior.

---

## 4.4 `services/` — Logic Layer

### Responsibility
Implements business behavior, workflows, coordination, and rules.

### This layer answers
- what business operation is being performed
- what steps need to happen
- what rules apply
- what recovery path exists if part of a workflow fails

### Contains
- cross-domain workflows
- multi-step business operations
- status transitions
- pseudonymous identity handling
- cross-database orchestration
- saga-style application-coordinated transactions where needed

### Does not contain
- Flask request parsing
- HTTP response construction
- route-specific concerns

### Allowed dependencies
- repositories
- ORM models
- domain objects
- optional assemblers
- API response models only if intentionally chosen as a return type

### Rules
- this is the only layer allowed to coordinate both databases at once
- services may call repositories for reads and repeated access patterns
- services may use ORM directly for writes where that is clearer
- services own recovery logic for cross-database workflows

### Examples
- create a linked submission across core and response databases
- resolve pseudonymous identity
- move a submission from `pending` to `stored` or `failed`

### Rule
If logic spans multiple repositories, multiple models, or multiple databases, it belongs here.

---

## 4.5 `api/routes/` — Request Layer

### Responsibility
Maps HTTP requests to service calls and maps service results back to HTTP responses.

### Contains
- route handlers
- request parsing
- request schema validation calls
- response schema serialization calls
- HTTP response return logic

### Does not contain
- SQL queries
- session management
- business rules
- cross-database workflow logic
- persistence decisions

### Required pattern
1. parse request input
2. validate with request schema
3. call one service method
4. serialize result with response schema
5. return HTTP response

### Rule
Routes are glue only.
They must stay thin.

---

## 5. Domain Objects and Aggregates

## 5.1 `domain/` — Application Meaning Layer

### Responsibility
Represents meaningful app-level concepts that are not the same thing as ORM rows or API payloads.

### Domain object
A domain object is an application-facing concept.
It exists because the app needs to think in terms more meaningful than raw storage models.

### Aggregate
An aggregate is a domain object composed from multiple related pieces that should be treated as one conceptual unit.

### Examples
- `LinkedSubmission`
- `SurveyAggregate`
- `SubmissionStatus`

### Typical use
Use a domain object or aggregate when a service naturally works with one meaningful concept backed by several ORM rows.

### Does not contain
- table mapping responsibility
- API contract responsibility
- direct HTTP concerns

### Rule
Domain objects express meaning.
They do not mirror tables just because tables exist.

---

## 6. Assemblers

## 6.1 `assemblers/` — Optional Construction Helpers

### Responsibility
Builds domain objects or aggregates from ORM objects or repository results.

### Relationship to other layers
- ORM = raw stored pieces
- repository = fetches pieces
- assembler = combines pieces
- service = decides when and why to build the result

### Use cases
Introduce an assembler when:
- composition logic is large
- composition logic is repeated
- the constructed object deserves a named construction pattern

### Do not use when
- the service can assemble the object cleanly inline
- the build logic is tiny or used once

### Rule
Assemblers build objects.
They do not own workflow behavior.

---

## 7. Request and Response Flow

## 7.1 Standard Request Flow

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

## 7.2 Internal Composition Flow

Inside the service layer, composition may look like this:

```text
ORM rows / repository results
    ↓
domain object / aggregate
    ↓
response schema
```

This allows services to work with meaningful application concepts rather than exposing raw ORM rows directly.

---

## 8. Cross-Database Rule

FlowForm uses two PostgreSQL databases.
Anything that coordinates both databases belongs in `services/` only.

### Implications
- no repository may coordinate core and response together
- no ORM relationship may span both databases
- no route may directly implement cross-database workflow logic
- recovery and reconciliation logic for partial failure belongs in services

### Design consequence
Cross-database workflows should use an application-coordinated transaction or saga-style pattern when consistency must be managed across both databases.

---

## 9. Practical Classification Guide

| Situation | Correct Layer |
|---|---|
| Defining a table column | `schema/orm/` |
| Validating an incoming JSON payload | `schema/api/requests/` |
| Shaping an outgoing API response | `schema/api/responses/` |
| Looking up a user by email | `repositories/` |
| Looking up a submission by shared id | `repositories/` |
| Writing a submission to both databases | `services/` |
| Assigning a pseudonymous UUID | `services/` |
| Loading several survey-related rows into one conceptual object | `services/` + optional `domain/` aggregate |
| Building a `SurveyAggregate` or `LinkedSubmission` | service or `assemblers/` |
| Returning an HTTP 201 response | `api/routes/` |
| Anything that touches two databases | `services/` only |

---

## 10. Anti-Patterns

The following are explicitly discouraged:

- business logic inside ORM models
- Pydantic models used as persistence models
- repositories that coordinate two databases
- routes that contain workflow logic
- routes that contain raw SQL or session management
- cross-database SQLAlchemy relationship hacks
- domain objects that merely duplicate a single table definition
- assemblers that own business decisions instead of object construction

---

## 11. Design Intent

This structure exists to keep the codebase understandable as it grows.

It aims to preserve:
- clear storage definitions
- explicit API contracts
- reusable database access patterns
- isolated business workflows
- meaningful application concepts
- clean object construction boundaries
- explicit handling of two-database workflows

### Summary
- `schema/api/` defines contracts
- `schema/orm/` defines storage
- `repositories/` define reusable access
- `services/` define behavior
- `domain/` defines meaning
- `assemblers/` define construction

That is the planned design pattern and application-layer model for the project.

