## Pass report

Pass: 04 — session-start

Changed files:
* `backend/app/services/public_submissions/core/session_starter.py` — wired response envelope creation into session start flow
* `backend/app/services/public_submissions/api/session_management.py` — added `response_db` parameter to `start_session()`
* `backend/app/api/v1/public.py` — route now passes `get_response_db()` to service
* `backend/app/repositories/core/submission_sessions.py` — added `mark_abandoned()` helper
* `backend/tests/integration/core/conftest.py` — added autouse `_mock_session_encryption` fixture
* `backend/tests/e2e/conftest.py` — added autouse `_mock_session_encryption` fixture
* `backend/tests/integration/core/test_session_start_envelope.py` — new: 5 cross-DB integration tests
* `backend/tests/integration/core/test_session_start_response_contract.py` — updated call signature
* `backend/tests/integration/core/test_flow_matrix.py` — updated call signature
* `backend/tests/integration/core/test_transaction_boundary.py` — updated call signature
* `backend/tests/unit/test_submission_session_contracts.py` — fixed pre-existing assertion for `survey_schema` field

Behavior implemented:
* After core session creation (flush, no commit), derives session locator via `derive_session_locator()`
* Generates 32-byte plaintext DEK via `os.urandom(32)`
* Wraps DEK with KMS via `wrap_dek()` using encryption context that includes session locator hex and KMS context version
* Creates response envelope via `response_envelope_repo.create()` with `crypto_version=1`, `kms_context_version=1`
* Commits response DB first, then core DB — resume token never returned until both succeed
* On any envelope creation failure (KMS, Secrets Manager, repo): rolls back core DB so session, single-use link consumption, and recognition-token side effects are undone
* Caches plaintext DEK in `DekCache` keyed by session locator after both commits succeed
* `SessionStartError` raised on envelope creation failure — translates `KmsError` and `LinkageSecretError`

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "session_start"` — 11 passed
* `bash backend/scripts/run-tests.sh --ai -k "session_start or flow_matrix or submission_session or transaction_boundary"` — 66 passed
* `bash backend/scripts/run-tests.sh --ai` — 425 passed (full suite, no regressions)

Failures or skipped validation:
* none

Policy change during pass:
* none

Trace notes:
* entry points touched: `start_submission_session()` route in `api/v1/public.py`
* service methods touched: `SessionStarter.start()`, `SessionStarter._create_response_envelope()`, `SessionStarter._get_encryption_settings()`, `SessionManagementService.start_session()`
* repository helpers touched: `submission_sessions.mark_abandoned()` (new)
* side effects changed: session start now creates a response envelope in the response DB; DEK is cached in worker memory
* transaction boundary changed: core commit now happens after response DB commit (was: core-only commit). Sequence is: core flush → response flush → response commit → core commit. On response failure, core rollback undoes all pending changes.
* tests that now describe behavior: `test_session_start_envelope.py::TestSuccessfulSessionStart::test_session_start_creates_core_session_and_response_envelope`, `test_session_start_envelope.py::TestSuccessfulSessionStart::test_dek_cached_after_successful_start`, `test_session_start_envelope.py::TestEnvelopeFailureRollback::test_kms_failure_rolls_back_core_session`, `test_session_start_envelope.py::TestEnvelopeFailureRollback::test_linkage_secret_failure_rolls_back_core_session`, `test_session_start_envelope.py::TestEnvelopeFailureRollback::test_envelope_repo_failure_rolls_back_core_session`

Remaining risks:
* `mark_abandoned()` was added to `submission_sessions` repo but is not yet called from the session starter — the current failure path rolls back core (session never committed). It would be needed if a flow exists where core commits before response creation. Current design avoids this, but reconciliation pass should verify.
* Existing integration and e2e tests use an autouse mock that patches `SessionStarter._create_response_envelope` — if that method's signature changes, all conftest mocks need updating.
* The `_CRYPTO_VERSION` and `_KMS_CONTEXT_VERSION` constants are hardcoded in `session_starter.py`. Future rotation support may need these read from config.

## Pass-forward

* `SessionStarter.start()` now takes `(db, response_db, *, payload, actor, recognition_token)` — second positional arg is the response DB session.
* `_create_response_envelope()` is the seam: it derives the session locator, generates+wraps the DEK, creates the envelope, and commits response DB. It returns `(session_locator, plaintext_dek)`.
* Session locator derivation uses `derive_session_locator(str(session.id), linkage_secret)` where `session.id` is the core `SubmissionSession.id` UUID.
* `EncryptionSettings` is accessed via `current_settings().flowform.encryption` or injected via constructor. Assert it's not `None` before use.
* `DekCache` is injected via constructor kwarg `dek_cache`. After successful start, the plaintext DEK is cached with key = `session_locator: bytes`. The session loader should check the cache before calling KMS unwrap.
* Existing integration/e2e tests mock `_create_response_envelope` via autouse fixtures in `tests/integration/core/conftest.py` and `tests/e2e/conftest.py`. New tests that exercise real envelope creation should override with `@pytest.fixture def _mock_session_encryption(): ...` (empty body).
* `SessionStartError` is the error type raised on envelope failure — the session loader and answer save paths may need to handle or translate it.
* KMS encryption context keys: `"session_locator"` (hex) and `"kms_context_version"` (string). The decrypt path must use the same context.
