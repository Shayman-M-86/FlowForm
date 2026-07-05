# DB Schema Changes — What to Check

When anything in the database changes — a column added or removed, a
constraint introduced or relaxed, a new table, a renamed FK — the change
ripples through about a dozen layers of FlowForm code. This document is the
**checklist of concerns** to walk through for any such change.

It is deliberately not a step-by-step procedure. Each change has its own
shape; this guide names the layers that are likely to need attention and
explains *why* so you can decide which apply. Skim top to bottom, touch
what matters, skip what doesn't.

Audience: backend engineers and AI coding agents working on this repo.

---

## The layers, in dependency order

A schema change does not happen in one place. It is a coordinated edit
across these layers — usually in this order, though small changes may skip
several of them.

### 1. SQL schema (`infra/postgres/init/schema/`)

The runtime source of truth for the database structure. Two files:

- `flowform_core_db_schema_v4.sql`
- `flowform_response_db_schema_v4.sql`

Things to consider when editing:

- **Constraint names matter.** The DB error translator
  (`app/db/error_handling/integrity_rules.py`) keys off the exact constraint
  name. Follow the conventions in
  `infra/postgres/init/schema/sqlalchemy_constraint_naming_rules.md`. A
  rename in the SQL file is a breaking change to every rule that targets
  the old name.
- **What can a CHECK express vs what needs a trigger?** Single-row,
  expression-based invariants → CHECK. State-machine guards that depend on
  other rows or current state → trigger function with a stable
  `RAISE EXCEPTION` message (matched via `message_rule`).
- **Response-DB isolation.** The response schema must never carry a real
  `user_id` — only the pseudonymous subject UUID. Apply this to any new
  column on a response-DB table.

### 2. ORM models (`app/schema/orm/`)

SQLAlchemy declarative models. Two roots: `models/core/` uses `CoreBase`,
`models/response/` uses `ResponseBase` — never mixed.

Things to consider:

- **Column shape matches the SQL.** Types, nullability, defaults. The SQL
  file is authoritative at runtime; ORM mismatches surface as test
  failures or runtime errors.
- **`__table_args__` carries only what the ORM needs — not a full mirror.**
  The DB is built from the SQL files, never from ORM metadata, so the ORM
  does not need to redeclare every constraint. Keep only the constraints
  SQLAlchemy actually uses: foreign keys (required by `relationship()`) and
  the composite UNIQUEs that composite FKs target. CHECK constraints and
  non-FK-referenced UNIQUEs live in the SQL schema only (the source of
  truth). Adding a CHECK or a standalone UNIQUE does **not** require an
  `__table_args__` entry.
- **No cross-DB relationships.** Core and response models share only the
  integer link `core.survey_submissions.id ↔ response.submissions.core_submission_id`.
- **No business logic in models.** Hybrid properties for read-only derived
  values are acceptable; mutation logic belongs in services.

### 3. Mock data (`infra/postgres/flowform_core_mock_data.sql`, `flowform_response_mock_data.sql`)

These seed local dev / test databases with realistic rows. They are
constrained by the schema — every CHECK, FK, and UNIQUE in the schema must
be satisfied by the mock data, or the seed transaction rolls back.

Things to consider:

- **New NOT NULL column?** Every existing `INSERT` in the mock file needs
  a value or a sensible default.
- **New CHECK constraint?** Audit the existing rows — does each one
  satisfy it? Rows that previously inserted fine may now be rejected.
- **New FK?** The referenced row must exist before the referrer.
- **Removed table or column?** Strip the matching `INSERT` lines and any
  `SELECT setval(...)` at the bottom.
- **Renamed constraint?** Doesn't directly affect mock data, but if the
  rename was prompted by a structural change, the rows likely need
  inspection too.

Run the seed locally after every schema change to confirm. If the seed
fails, the schema and the mock data have diverged.

### 4. Pydantic request schemas (`app/schema/api/requests/`)

The first line of validation. Anything a client can send goes here.

Things to consider:

- **Is the new/changed field client-facing?** If yes, validate it in
  Pydantic *before* it reaches the service. Cheaper than a DB rejection,
  produces a clean 422 with field-level error info, and works for every
  endpoint that uses the schema.
- **Multi-field invariants** (`X requires Y`, `A is incompatible with B`)
  → `@model_validator(mode="after")`.
- **Size or structural caps that mirror DB CHECKs** → a model validator
  that serialises the field and checks byte length. Keep the constant in
  the Pydantic file with a comment referencing the SQL CHECK name so
  future-you can keep them in sync. See
  `app/schema/api/requests/content/node.py:_MAX_NODE_CONTENT_BYTES` for
  the pattern.
- **PATCH semantics.** Partial-update schemas use `Optional` fields and
  rely on `model_fields_set` so the service can distinguish "field omitted"
  from "field explicitly null." Adding a new optional field is safe; making
  a previously-optional field required is breaking.

### 5. Pydantic response schemas (`app/schema/api/responses/`)

What the API returns. Adding a column to the DB doesn't automatically
expose it — the response schema decides.

Things to consider:

- **Is the new column meant to be public?** Audit-style timestamps and
  internal counters often should not be in responses.
- **Response-DB isolation.** A response payload going to a public-link
  caller must never reveal core-DB user identifiers.
- **Backwards compatibility.** Removing a field from a response is a
  breaking change to any consumer; renaming is breaking too.

### 6. Domain rules (`app/domain/`)

Business invariants that need current state, multi-step reasoning, or a
specific error code. Lives between Pydantic (stateless validation) and the
DB (final enforcement).

Things to consider:

- **PATCH coherence checks** belong here. Pydantic only sees the patch;
  the rule sees the patch merged onto the current record. Example:
  `survey_rules.ensure_visibility_slug_coherent` is called by
  `services/surveys.py:update_survey` after merging.
- **State-machine transitions** (publish, archive, unpublish) belong here.
  The rule reads the current status and rejects bad transitions with a
  specific `AppError` subclass.
- **New error class needed?** If the rejection reason is distinct from
  existing codes, add a new `AppError` subclass in `app/domain/errors.py`.
  Use 409 for state conflicts, 422 for structural payload invariants.

### 7. Service layer (`app/services/`)

Orchestrates upstream validation and database writes. The only layer
allowed to touch both databases.

Things to consider:

- **Call the domain rule before the repo write.** The rule should fail
  fast with a clean 422/409 — that is much cheaper than a DB rollback.
- **Compute merged state for PATCH coherence.** Use
  `payload.model_fields_set` to detect which fields the client actually
  sent, then merge against the loaded record before calling the rule.
- **Pass the right contexts to `commit_with_err_handle`** /
  `flush_with_err_handle`. The context list is what the DB integrity rule
  registry matches against; missing contexts mean missing translations.

### 8. Repository (`app/repositories/`)

One DB per repo, named query helpers, no workflow logic.

Things to consider:

- **Honour `model_fields_set` on partial updates.** Only mutate fields the
  client explicitly sent. See `surveys_repo.py:update_survey` for the
  pattern.
- **`flush_with_err_handle(db, contexts=[...])` not `db.flush()`** when
  the mutation can trigger an integrity rule. Bare flushes bypass the
  translation layer and surface as raw 500s via the Flask-level
  `handle_integrity_error` fallback.

### 9. DB integrity rules (`app/db/error_handling/integrity_rules.py`)

The translator between Postgres constraint violations and `AppError`
codes. Read the module docstring for the full philosophy.

Things to consider:

- **Does the new CHECK need a rule?** Decision flow:
  - Covered by Pydantic / domain → leave the CHECK as defence in depth, do
    *not* register a rule. If the CHECK fires, the unmatched-rule path
    raises a 500, which correctly signals an upstream bypass.
  - Race-prone uniqueness, cross-table referential, or trigger-enforced
    state-machine → register a 409 rule.
  - CHECK on a server-controlled field that clients cannot set → register
    a 500 rule with a "server invariant violated" message (see
    `ck_survey_submissions_status_valid` for the pattern).
- **Constraint name in the rule must match the SQL exactly.** Mismatch =
  silently unmatched = 500 on every fire.
- **Update the module docstring's worked-example list** if you add or
  remove a rule that appears there.

### 10. Tests (`tests/`)

Three layers of test live here, each with a different question to answer.

Things to consider:

- **Unit tests** on the new domain rule. Cover the happy path plus each
  way the rule can raise.
- **Service-level integration test.** Cover the upstream rejection (Pydantic
  or domain rule) plus the happy path. Use the test session fixtures
  documented in `.claude/rules/backend-tests.md`.
- **Schema-level integration test** when the invariant is structural.
  Style: `tests/integration/core/test_surveys.py` — bypass the service,
  hit the raw CHECK via `db.flush()`, assert on the constraint name. These
  catch regressions in the SQL file itself.

### 11. OpenAPI documentation (`app/openapi/`)

Mostly automatic, but a few things to verify.

Things to consider:

- **New `AppError` subclass?** The discovery layer in
  `app/openapi/error_examples.py` instantiates every subclass with stub
  args. If the constructor is unusual (required kwargs without type hints,
  no zero-arg path, raises on stub values) the class will be skipped and
  logged as a warning. Either add reasonable type annotations or accept
  the omission.
- **New request schema?** `@openapi_route(request_model=...)` registers it
  automatically. The discriminated-union schemas already produce rich
  Swagger examples, so nothing extra is needed.
- **New integrity rule?** Examples auto-derive from `RULES_BY_CONTEXT`.
  Verify the rule key (constraint name) sanitises into a readable
  `examples:` key — long trigger messages will produce ugly keys but
  remain valid.
- **Restart the Flask process** to bust the in-process spec cache after
  changes.

---

## Cross-cutting concerns

Apply these across all the layers above, not just one of them.

### Status-code choice for new errors

- **409 Conflict** — request was syntactically valid but collided with
  current state (uniqueness, FK, state-machine). Client may retry with
  different inputs or after state changes.
- **422 Unprocessable Entity** — request payload is structurally invalid
  on its own terms. Same semantic as Pydantic's 422. Use for multi-field
  domain rules where the client could fix the error by sending different
  values.
- **500 Internal Server Error** — invariant violation that the client
  could not have caused (server-controlled field, missing rule, code
  bypass). The message should explicitly say "server invariant violated."
- **400, 404** — useful at the API layer, but rare from `integrity_rules`.
  Those conditions are cheaper to detect with a service-level read.

### Defence in depth

The DB CHECK / FK / trigger is the final guarantor. Upstream layers
(Pydantic, domain rules) exist for *fast failure* and *clean error
messages*, not as a replacement for the DB constraint. A schema change
that adds a new invariant should usually land all three:

1. The DB constraint (final guarantee).
2. A Pydantic or domain check (fast feedback, clean 422).
3. *Either* a translation rule in `integrity_rules.py` (when the CHECK
   could legitimately fire under concurrency or via non-API paths) *or* a
   comment explaining where the upstream guard lives (when it cannot).

### Naming conventions

- **DB constraints** — follow `sqlalchemy_constraint_naming_rules.md`.
  Example shapes: `ck_<table>_<predicate>`, `uq_<table>_<columns>`,
  `fk_<from_table>_<to_table>_<column>`.
- **Error codes** — uppercase snake case, descriptive, stable. Once a
  client may depend on a code, treat it as part of the public API.
- **Error classes** — `<Subject><Condition>Error`, e.g.
  `SurveyVisibilityMismatchError`, `SubmissionInvalidTimestampsError`.

### Backwards compatibility

- Adding a nullable column is safe.
- Adding a NOT NULL column requires a default value or a migration that
  populates existing rows first.
- Adding a CHECK to an existing column requires that all existing rows
  already satisfy it (including in the mock-data file).
- Removing or renaming a column or constraint is breaking — update every
  reference in the same change, including the mock data and any
  integrity rules.

---

## Worked examples from this codebase

Three recent changes illustrate the patterns. Reading the diffs alongside
this checklist is the fastest way to see how the pieces fit.

### A constraint moved from DB-only to upstream

The slug/visibility coherence rules on `surveys` were originally enforced
*only* by two CHECK constraints (`ck_surveys_public_requires_slug`,
`ck_surveys_slug_requires_public_visibility`) and translated to 422 by
`integrity_rules.py`. The PATCH update path could not be guarded by
Pydantic (which sees only the patch, not the current record), so 422s
surfaced via DB rejection.

Resolution:

- Added `SurveyVisibilityMismatchError(AppError)` (422) in
  `app/domain/errors.py`.
- Added `survey_rules.ensure_visibility_slug_coherent()` in
  `app/domain/survey_rules.py`.
- Wired the rule into `services/surveys.py:update_survey` after merging
  `model_fields_set` against the loaded record.
- Removed the two integrity rules from `integrity_rules.py`, leaving a
  comment explaining where the upstream guards live.
- Kept the DB CHECKs as defence in depth.

### A CHECK kept but flipped to 500

`ck_survey_versions_published_requires_schema_and_timestamp` enforces that
a published version has both a compiled schema and a published timestamp.
The fields involved are not exposed in any request schema — only
`surveys_repo.publish_version` writes them, atomically. The CHECK cannot
fire from an API call.

Resolution:

- Kept the integrity rule but changed its status from 422 to 500.
- Rewrote the message to say "Server invariant violated: ... This
  indicates a code path bypassed `surveys_repo.publish_version`."
- Added an inline comment block above the rule explaining why no Pydantic
  guard exists and what it means if the CHECK ever fires.

The same pattern applied to `ck_survey_submissions_status_valid`.

### A new constraint with a Pydantic mirror

`ck_survey_questions_schema_size` caps the serialised JSON of a node at
10 000 bytes. Reachable from the API because deeply nested payloads with
long labels can exceed it.

Resolution:

- Added `_MAX_NODE_CONTENT_BYTES = 10_000` in
  `app/schema/api/requests/content/node.py` with a comment cross-referencing
  the SQL CHECK.
- Added a `@model_validator(mode="after")` on both `CreateNodeRequest` and
  `UpdateNodeRequest` that serialises `content` with `by_alias=True` and
  rejects oversized payloads.
- Removed the integrity rule, leaving a comment block explaining the
  upstream guard and noting the constant must stay in sync with the SQL.
- Kept the DB CHECK as defence in depth.

---

## Quick reference: the file map

| Concern | File / dir |
|---|---|
| SQL schema | `infra/postgres/init/schema/flowform_*_db_schema_v4.sql` |
| Constraint naming rules | `infra/postgres/init/schema/sqlalchemy_constraint_naming_rules.md` |
| Mock data | `infra/postgres/flowform_*_mock_data.sql` |
| ORM models | `app/schema/orm/{core,response}/` |
| Request schemas | `app/schema/api/requests/` |
| Response schemas | `app/schema/api/responses/` |
| Domain rules | `app/domain/` |
| Domain errors | `app/domain/errors.py` |
| Services | `app/services/` |
| Repositories | `app/repositories/` |
| DB integrity rules | `app/db/error_handling/integrity_rules.py` |
| DB error classes | `app/db/error_handling/errors.py` |
| API error handlers | `app/api/utils/errors.py` |
| Tests | `tests/{unit,integration}/` |
| OpenAPI examples | `app/openapi/error_examples.py` |
