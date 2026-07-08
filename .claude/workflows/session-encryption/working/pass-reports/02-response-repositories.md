## Pass report

Pass: 02 — response-repositories

Changed files:

* `backend/app/repositories/response/__init__.py` (new)
* `backend/app/repositories/response/response_envelope_repo.py` (new)
* `backend/app/repositories/response/response_answer_repo.py` (new)
* `backend/app/repositories/response/response_answer_revision_repo.py` (new)
* `backend/tests/integration/response/test_response_repos.py` (new)
* `.claude/workflows/session-encryption/working/targets/02-response-repositories/spec.md` (fixed: removed erroneous `aad` param from revision `create`, corrected all ID types from `int`/`str` to `uuid.UUID`)

Behavior implemented:

* `response_envelope_repo.create` — inserts envelope row with `flush_with_err_handle`
* `response_envelope_repo.get_by_locator` — looks up envelope by `session_locator` bytes
* `response_answer_repo.get_or_create` — inserts answer row inside `begin_nested()`, catches `IntegrityError` on `uq_response_answers_envelope_id_answer_locator`, re-fetches on race
* `response_answer_repo.get_by_locator` — looks up answer by `(envelope_id, answer_locator)`
* `response_answer_repo.lock_for_update` — `SELECT ... FOR UPDATE` on answer row
* `response_answer_revision_repo.create` — inserts revision row with `flush_with_err_handle`
* `response_answer_revision_repo.get_by_mutation_id` — idempotency lookup by `(answer_id, client_mutation_id)`
* `response_answer_revision_repo.get_latest` — follows `ResponseAnswer.latest_revision_id` pointer
* `response_answer_revision_repo.get_history` — returns all revisions ordered by `revision_number` ascending
* `response_answer_revision_repo.update_latest_pointer` — sets `latest_revision_id` on the answer row

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "response_repo"` — 13 passed

Failures or skipped validation:

* none

Policy change during pass:

* Removed `aad: bytes` parameter from `ResponseAnswerRevisionRepo.create` in the spec. AAD is built by the crypto layer and passed to AES-GCM; it is not stored or accepted by the repository. The ORM model and SQL schema have no `aad` column.
* Corrected all ID type annotations in the spec from `int`/`str` to `uuid.UUID` to match the ORM models.
* Added `envelope_id: uuid.UUID` to the revision `create` signature — required by the composite FK `fk_response_answer_revisions_answer_same_envelope`.
* Added `latest_revision_id: uuid.UUID` to `get_or_create` — required by the NOT NULL column with deferred FK.

Trace notes:

* entry points touched: none (repos only)
* service methods touched: none
* repository helpers touched: `response_envelope_repo.create`, `response_envelope_repo.get_by_locator`, `response_answer_repo.get_or_create`, `response_answer_repo.get_by_locator`, `response_answer_repo.lock_for_update`, `response_answer_revision_repo.create`, `response_answer_revision_repo.get_by_mutation_id`, `response_answer_revision_repo.get_latest`, `response_answer_revision_repo.get_history`, `response_answer_revision_repo.update_latest_pointer`
* side effects changed: none
* transaction boundary changed or unchanged: unchanged — repos flush only, no commits
* tests that now describe behavior: `TestResponseEnvelopeRepo`, `TestResponseAnswerRepo`, `TestResponseAnswerRevisionRepo` in `test_response_repos.py`

Remaining risks:

* `get_or_create` uses `begin_nested()` + manual `IntegrityError` catch rather than `flush_with_err_handle`. This is intentional — the race recovery needs to rollback the savepoint and re-query, not translate to an AppError. Future service code must be aware that `get_or_create` manages its own savepoint.
* The `latest_revision_id` deferred FK means the answer row is created with a placeholder UUID that the service must update before commit. If the service forgets, the commit will fail with an FK violation.

## Pass-forward

* Response repos live at `backend/app/repositories/response/`; import via `from app.repositories.response import response_envelope_repo, response_answer_repo, response_answer_revision_repo`.
* All IDs are `uuid.UUID` (not `int`). All locators and nonces are `bytes`.
* `response_envelope_repo.create` requires `session_locator`, `linkage_key_version`, `wrapped_dek`, `kms_key_arn`, `kms_context_version`, `crypto_version`.
* `response_answer_repo.get_or_create` requires `envelope_id`, `answer_locator`, and `latest_revision_id` (deferred FK — service must set the real revision ID before commit).
* `response_answer_revision_repo.create` requires `answer_id`, `envelope_id`, `revision_number`, `nonce`, `ciphertext`, `client_mutation_id`. No `aad` param — AAD is handled by the crypto layer before calling the repo.
* `get_or_create` manages its own savepoint internally; callers should not wrap it in an additional `begin_nested()`.
* `lock_for_update` returns `ResponseAnswer | None` — service must check for `None`.
* Repos flush only; commits are the service's responsibility.
