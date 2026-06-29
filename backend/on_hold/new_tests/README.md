# New Test Suite Structure

This folder is a planning scaffold for a cleaner backend test suite. The
existing files are intentionally concept-only Python modules. They describe the
behaviour each future test file should own, without implementing the tests yet.

Use this guide to keep future implementation work explicit, layered, and easy
to navigate.

## Rule Of Thumb

- `new_tests/conftest.py` owns global app, config, database, auth, and crypto
  basics.
- `new_tests/unit/conftest.py` should own unit-only mocks, fakes, and
  monkeypatch helpers if or when it is added.
- `new_tests/integration/conftest.py` should own real DB sessions,
  transaction rollback, and seeded database helpers if or when it is added.
- `new_tests/e2e/conftest.py` should own Flask client, HTTP auth, cookie, and
  route helpers if or when it is added.
- `new_tests/factories/` should be imported explicitly. Factories should create
  raw database state, not hide behaviour behind fixtures.
- `new_tests/scenarios/` should be imported explicitly. Scenarios should build
  meaningful test worlds from factories.

## Core Principle

A test file should answer one question:

> What behaviour owns this?

Prefer feature and use-case folders over vague technical buckets. For example:

- Prefer
  `new_tests/integration/services/public_submissions/access_resolution/test_private_access_matrix.py`
  over `new_tests/integration/core/test_flow_matrix.py`.
- Prefer
  `new_tests/integration/services/public_submissions/session_start/test_start_response_envelope.py`
  over `new_tests/integration/core/test_session_start_envelope.py`.
- Prefer
  `new_tests/integration/services/public_submissions/recognition/test_token_actions.py`
  over `new_tests/integration/core/test_token_action.py`.

## Dependency Shape

| Path | Fixture source | Main purpose |
| --- | --- | --- |
| `new_tests/conftest.py` | self | Global fixtures: app, config, DB engines, fake auth, fake crypto clients |
| `new_tests/unit/conftest.py` | root | Unit-only fakes, mocks, monkeypatch helpers |
| `new_tests/integration/conftest.py` | root | Real DB sessions, transaction rollback, seeded database helpers |
| `new_tests/e2e/conftest.py` | root | Flask client, auth headers, cookies, request helpers |
| `new_tests/factories/` | explicit imports | Raw database object creation |
| `new_tests/scenarios/` | explicit imports | Larger reusable test worlds |

Only `new_tests/conftest.py` exists in the initial scaffold. The other
conftest files should be added only when the suite starts needing that layer of
fixtures.

## Fixture Boundaries

### `new_tests/conftest.py`

Keep only broad, cross-suite fixtures here:

- `app`
- `test_config`
- `db_engine`
- `response_db_engine`
- `db_session_factory`
- `response_db_session_factory`
- `fake_auth_user`
- `fake_kms_client`
- a shared clock/freezing helper if it is used everywhere

Do not put feature-specific setup here. If a fixture only serves one domain or
one workflow, make it a factory, scenario helper, or local fixture near the
tests that use it.

### `new_tests/unit/conftest.py`

Use this for unit-only helpers:

- `mock_db`
- `mock_response_db`
- `fake_repo`
- `fake_cache`
- `fake_linkage_key`
- `fake_session_context`
- `fake_response_context`
- `monkeypatch_crypto_clients`

Unit tests should isolate rules, schema parsing, primitives, and service
orchestration. They should avoid real database sessions unless the thing under
test is explicitly a DB integration boundary.

### `new_tests/integration/conftest.py`

Use this for DB-backed fixtures:

- `db`
- `response_db`
- `clean_database`
- `transactional_db`
- `transactional_response_db`
- `seed_default_roles`
- `seed_linkage_key`
- `seed_default_response_store`
- `integration_crypto_config`

Integration tests should prove repositories and services work with real schema,
real transactions, and the core/response database split.

### `new_tests/e2e/conftest.py`

Use this for HTTP/API helpers:

- `client`
- `auth_headers`
- `admin_auth_headers`
- `respondent_cookies`
- `set_resume_cookie`
- `set_recognition_cookie`
- `api_post`
- `api_get`
- `api_delete`

E2E tests should stay small. They prove a real user flow through HTTP,
including status codes, cookies, auth, and response bodies.

## Factories

Factories should create raw state. They should receive dependencies as explicit
arguments instead of pulling from hidden pytest fixtures.

| File | Dependency style | Role |
| --- | --- | --- |
| `new_tests/factories/users.py` | explicit `db` arg | users, verified users, auth identities, public IDs |
| `new_tests/factories/projects.py` | explicit `db` arg | projects, owners, members, role assignments |
| `new_tests/factories/surveys.py` | explicit `db` arg | surveys, versions, content, visibility states |
| `new_tests/factories/survey_links.py` | explicit `db` arg | general, private invite, assigned, expired, used, inactive links |
| `new_tests/factories/subjects.py` | explicit `db` arg | subjects, identities, participant identity, recognition tokens |
| `new_tests/factories/submission_sessions.py` | explicit `db` arg | in-progress, completed, expired, abandoned sessions |
| `new_tests/factories/response_store.py` | explicit `db` and `response_db` args | response stores, envelopes, encrypted answers, revisions |
| `new_tests/factories/crypto.py` | no DB, or explicit fake crypto arg | fake keys, fake DEKs, deterministic locators |

Good factory shape:

```python
from new_tests.factories.surveys import create_published_survey


survey = create_published_survey(db, project=project)
```

Avoid factory functions that silently reach into global fixtures or mutate more
state than the function name promises.

## Scenarios

Scenarios build larger reusable worlds from factories. They should be readable
from the call site and should not become hidden fixture graphs.

| File | Dependency style | Role |
| --- | --- | --- |
| `new_tests/scenarios/respondent.py` | receives `db`, `response_db` | public survey, link, subject, session, answer-save scenarios |
| `new_tests/scenarios/studio.py` | receives `db` | projects, members, roles, surveys, versions |
| `new_tests/scenarios/admin_responses.py` | receives `db`, `response_db` | completed sessions, encrypted answers, response history |

Good scenario shape:

```python
from new_tests.scenarios.respondent import public_survey_with_one_question


scenario = public_survey_with_one_question(db, response_db)
```

## Layer Intent

### Unit

Unit tests are for isolated rules, classes, functions, schema contracts, crypto
primitives, cache behaviour, and service branching with mocked dependencies.

Use unit tests for:

- pure domain rules
- schema validation and serialization
- crypto primitives and deterministic helper behaviour
- cache item and registry behaviour
- service orchestration decisions where repositories can be mocked

Do not use unit tests to prove cross-database consistency or full public
submission flows. Those belong in integration tests.

### Integration

Integration tests are for real DB state, repositories, service flows, and
cross-database behaviour.

Use integration tests for:

- repository CRUD and constraints
- core DB and response DB separation
- session start, answer save, completion, recognition, and access resolution
- admin response decryption, export, and deletion
- studio project/survey lifecycle services
- account bootstrap and response store setup

These should become the highest-confidence backend tests for public submission
work because those flows cross validation, session state, encryption,
repositories, events, and both databases.

### E2E

E2E tests are for real HTTP route flows. Keep them fewer and broader than
integration tests.

Use E2E tests for:

- respondent survey start, answer save, resume, and completion
- private invite and authenticated link flows
- studio project, survey, link, and response-admin flows
- account bootstrap and profile update
- system health and OpenAPI availability

E2E tests should assert route behaviour: status codes, cookies, auth behaviour,
and response bodies.

## Public Submission Focus

The public submission workflow should be split by use-case:

- `session_start/` proves access resolution, subject resolution, session
  creation, response envelope creation, single-use link handling, transaction
  cleanup, and session-cache writes.
- `answer_save/` proves question validation, answer state handling, encryption,
  slot writes, response answer writes, revisions, session guards, and failure
  boundaries.
- `completion/` proves completed status transitions, event recording,
  idempotency decisions, and cache eviction.
- `events/` proves question-viewed and submission lifecycle event persistence.
- `access_resolution/` proves public, link-only, and private survey access
  matrices.
- `recognition/` proves recognition-token lookup, token actions,
  authenticated account linking, and subject merge reconciliation.

If a test crosses several of those concerns, prefer one integration test in the
owning workflow plus smaller tests in the dependent workflow. Avoid one large
matrix file that tries to own everything.

## Avoid Hidden Fixture Graphs

Avoid this style:

```text
new_tests/integration/core/conftest.py
new_tests/integration/response/conftest.py
new_tests/integration/models/conftest.py
new_tests/integration/environment/conftest.py
```

That makes dependencies too implicit and too hard to trace.

Prefer this style:

```text
new_tests/integration/conftest.py
new_tests/factories/*.py
new_tests/scenarios/*.py
```

Then each test imports its dependencies clearly:

```python
from new_tests.factories.survey_links import create_general_link
from new_tests.scenarios.respondent import public_survey_with_one_question
```

That gives the suite structure without turning pytest fixtures into a mystery
dependency graph.

## Current Scaffold Notes

The initial scaffold contains concept-only files for the main unit,
integration, and E2E areas. The pasted fixture plan also mentions a few future
files that are not part of the current scaffold, such as:

- `new_tests/unit/conftest.py`
- `new_tests/integration/conftest.py`
- `new_tests/e2e/conftest.py`
- `new_tests/factories/__init__.py`
- `new_tests/scenarios/__init__.py`
- additional targeted files like `test_cache_registry.py`,
  `test_invalid_link_states.py`, and `test_subject_merge_reconciliation.py`

Add those only when implementation work needs them. The goal is not to create
files for their own sake. The goal is a test suite where fixture ownership,
database boundaries, and workflow ownership are obvious at the file path.
