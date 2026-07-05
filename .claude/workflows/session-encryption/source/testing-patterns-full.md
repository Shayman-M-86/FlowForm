# Testing Patterns — Full Reference

## Runner

Use the Docker-based backend runner from the repo root. Prefer `-k` filters over
file paths so selection survives file moves:

```bash
bash backend/scripts/run-tests.sh --ai
bash backend/scripts/run-tests.sh --ai -k "session or response"
```

## Scope

- `backend/tests/unit/`: pure logic only; no DB fixtures.
- `backend/tests/integration/`: real DB fixtures for repos and services.
- `backend/tests/e2e/`: full Flask route stack and auth seams.

Put tests at the lowest scope that proves the behaviour.

## DB Fixtures

- `core_db_session`: core DB only.
- `response_db_session`: response DB only.
- `db_sessions`: explicit cross-DB tests; yields `.core` and `.response`.
- `db_session`: legacy mixed bind; avoid for new tests.

The DB fixtures use savepoint-backed sessions and outer transaction rollback.
Use `flush()` to materialise IDs. Avoid `commit()` unless the commit itself is
the behaviour under test.

## Factories

Use `backend/tests/integration/core/factories.py` for common core rows. Most
helpers return transient ORM objects; add them to the right session, then flush:

```python
user = make_user()
core_db_session.add(user)
core_db_session.flush()
```

Available helpers include `make_user`, `make_project`, `make_response_store`,
`make_survey`, `make_survey_version`, `make_survey_question`,
`make_survey_public_link`, `make_participant_chain`, and `make_token_pair`.
`make_participant_chain()` is the exception: pass a session and it adds/flushes
the subject, identity, and participant rows internally.

`make_token_pair()` returns `(raw_token, token_prefix, token_hash)` for browser
resume tokens and public-link tokens.

## Response DB Routing

`ResponseEnvelope`, `ResponseAnswer`, and `ResponseAnswerRevision` are response
DB models. Use `response_db_session` for direct response-row tests, or
`db_sessions` when a service crosses core and response DBs.

If routing is the behaviour under test, reuse `assert_model_uses_response_db()`
from `backend/tests/integration/response/test_db_routing.py`.

## Unit Style

Do not use DB fixtures in unit tests. Inject bytes, dicts, fakes, or
monkeypatches directly. Assert deterministic outputs exactly, and assert the
specific exception type the implementation exposes rather than catching bare
`Exception`.
