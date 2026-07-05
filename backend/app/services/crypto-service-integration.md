# Crypto Service Integration — Status and Remaining Work

## What was done

### New file: `public_submissions/core/shared/crypto_provider.py`

Factory function that builds the crypto service graph from `EncryptionSettings`.
Centralises AWS credential wiring so orchestrators receive ready-to-use service
instances instead of threading credentials through every call site.

```
build_crypto_services(enc?) -> CryptoServices
    .linkage_key_service   : LinkageKeyService
    .locator_service       : LocatorService
    .dek_service           : SessionDEKService
    .answer_crypto_service : AnswerCryptoService
```

---

### Changed: `public_submissions/core/actions/session_starter.py`

| Before | After |
|---|---|
| Imported `os`, `get_linkage_secret`, `wrap_dek`, `derive_session_locator`, `DekCache` | Imports `LocatorService`, `SessionDEKService` from `app.crypto.services` |
| `_create_response_envelope` called raw crypto functions inline | Delegates to `locator_service.for_new_session()` and `dek_service.create_for_session()` |
| `_DEK_LENGTH`, `_KMS_CONTEXT_VERSION` constants owned locally | DEK generation moved into `SessionDEKService`; `_KMS_CONTEXT_VERSION` kept (passed as encryption context) |
| `DekCache` injected and managed in `__init__` | Removed — `SessionDEKService` owns its own cache |
| No `linkage_key_version` on session creation | Calls `locator_service.get_current_linkage_key_version(db)` before `create_session` |

Constructor injection uses lazy initialisation (`_ensure_crypto()`) to avoid
calling `current_settings()` at import time — `SessionManagementService` is
instantiated at module level in `api/v1/respondent/__init__.py`.

---

### Changed: `public_submissions/core/shared/session_loader.py`

| Before | After |
|---|---|
| Imported `get_linkage_secret`, `derive_session_locator` | Uses `LocatorService.for_existing_session()` |
| Read raw secret, passed to `derive_session_locator` | `locator_service` kwarg, default-constructs via `build_crypto_services` |

The function signature gained `locator_service: LocatorService | None = None`
as an optional kwarg — fully backward compatible.

---

### Changed: `public_submissions/core/actions/answer_save.py`

| Before | After |
|---|---|
| Imported `get_linkage_secret`, `derive_answer_locator`, `unwrap_dek`, `encrypt_answer`, `generate_nonce`, `build_plaintext_payload`, `build_aad` | Imports `LocatorService`, `SessionDEKService`, `AnswerCryptoService`, and `build_aad` only |
| `_derive_answer_locator` helper called raw functions | `locator_service.answer_locator(...)` |
| `_get_or_unwrap_dek` managed DekCache + unwrap inline | `dek_service.get_for_session(...)` (cache-aware) |
| Encryption done with raw `build_plaintext_payload` + `generate_nonce` + `encrypt_answer` | `answer_crypto_service.encrypt(dek, question_node_id, answer_state, answer_value, aad)` |
| `DekCache` injected in `__init__` | Removed — `SessionDEKService` owns its own cache |

`build_aad` remains in the orchestrator (intentional — AAD binds ciphertext to
envelope/answer/revision IDs, which are persistence-layer concepts the crypto
services should not know about).

---

### Changed: `public_submissions/core/actions/admin_decrypt.py`

| Before | After |
|---|---|
| Imported `get_linkage_secret`, `derive_session_locator`, `unwrap_dek`, `decrypt_answer`, `parse_plaintext_payload`, `build_aad` | Imports `LocatorService`, `SessionDEKService`, `AnswerCryptoService`, and `build_aad` only |
| `_load_envelope_and_dek` called raw crypto inline | Delegates to `locator_service.for_existing_session()` + `dek_service.get_for_session()` |
| `_decrypt_revision` called raw `build_aad` + `decrypt_answer` + `parse_plaintext_payload` | Delegates to `answer_crypto_service.decrypt(dek, ciphertext, nonce, aad)` |

Services injected as optional kwargs to the public functions
(`decrypt_session_detail`, `decrypt_session_history`). `_load_envelope_and_dek`
now takes a core `db` parameter (needed by `LocatorService` to look up linkage
key versions from the `linkage_key_versions` table).

---

### Changed: `crypto/services/locator_service.py`

Added `get_current_linkage_key_version(db) -> int` — returns the current key
version without deriving a locator. Needed by `SessionStarter` to set
`linkage_key_version` on the session row before flushing.

---

### Changed: `repositories/core/submission_sessions.py`

`create_session()` gained `linkage_key_version: int | None = None` parameter.
The `linkage_key_versions` table was added in commit `d252e20` with a NOT NULL
FK on `submission_sessions.linkage_key_version`, but `create_session` was never
updated to accept the value — this was a pre-existing gap surfaced by the
refactoring.

---

### Changed: `tests/conftest.py`

Added `_seed_linkage_key_version()` to `core_db_session` fixture — inserts a
`linkage_key_versions` row with `version=1` so the NOT NULL FK constraint
passes in all integration tests.

---

### Changed test files

All test files were rewritten to inject mock crypto services via constructor
instead of patching module-level function imports:

| Test file | What changed |
|---|---|
| `tests/integration/core/conftest.py` | Autouse fixture now patches `SessionStarter.__init__` to inject mock `LocatorService` + `SessionDEKService` |
| `tests/integration/core/test_answer_save.py` | Uses `AnswerSaveService(locator_service=..., dek_service=..., answer_crypto_service=...)` |
| `tests/integration/core/test_session_start_envelope.py` | Uses `SessionStarter(locator_service=..., dek_service=..., encryption_settings=...)` |
| `tests/unit/services/test_session_loader.py` | Passes `locator_service=` kwarg to `load_current_session()` |
| `tests/integration/response/test_session_start_encryption.py` | Full rewrite with mock service injection |
| `tests/integration/response/test_answer_save_encryption.py` | Full rewrite with mock service injection |
| `tests/integration/response/test_admin_decrypt.py` | Full rewrite with mock service injection |
| `tests/e2e/conftest.py` | Patches `SessionStarter.__init__` instead of `_create_response_envelope` |

---

## Design decisions

### `build_aad` stays in orchestrators

AAD binds ciphertext to envelope/answer/revision IDs — persistence-layer
identifiers. The crypto services are deliberately unaware of envelopes,
answers, and revisions. The orchestrator constructs AAD and passes it as opaque
`bytes` to `AnswerCryptoService.encrypt()` / `.decrypt()`.

### `DekCache` removed from orchestrators

`SessionDEKService` has its own internal cache keyed by `(session_id,
kms_key_arn)`. The old standalone `DekCache` keyed by `session_locator` is no
longer needed. This eliminates the manual put/get pattern that was spread across
`SessionStarter`, `AnswerSaveService`, and the tests.

### Lazy initialisation in constructors

`SessionManagementService` is instantiated at module level in
`api/v1/respondent/__init__.py`, which triggers `SessionStarter.__init__` at
import time — outside any Flask app context. The `_ensure_crypto()` method
defers `build_crypto_services()` to first method call, when the app context
exists.

---

## Current audit: 2026-06-22

Checked against the current checkout after the `core/actions`, `core/shared`,
and `core/resolution` package split.

### Done: `deletion.py`

`services/public_submissions/core/actions/deletion.py` is no longer a deferred
item. It imports `LocatorService`, calls `loc_svc.for_existing_session(...)`,
and resolves crypto services through
`services/public_submissions/core/shared/session_crypto.py`.

### Done: `completion.py`

`completion.py` still has no crypto work. It only uses `SessionContext`; no
service-graph work is needed.

### Done: Category 3 answer-save validation

The old Category 3 note is fixed. The current answer-save tests no longer pass
plain strings such as `"hello"` for field-family questions. They use structured
short-text payloads such as:

```python
answer_value={"field_type": "short_text", "text": "hello"}
```

The focused integration run confirmed the answer-save groups are no longer in
the failure list.

---

## Remaining test failures from the focused audit

Command used:

```bash
bash scripts/run-tests.sh --ai -q \
  tests/integration/core/test_answer_save.py \
  tests/integration/response/test_answer_save_encryption.py \
  tests/integration/response/test_deletion_encryption.py \
  tests/integration/response/test_completion_encryption.py \
  tests/integration/response/test_admin_decrypt.py \
  tests/integration/core/test_flow_matrix.py \
  tests/integration/core/test_session_start_response_contract.py \
  tests/integration/core/test_transaction_boundary.py \
  tests/integration/core/test_session_start_envelope.py
```

Current result shape:

- The answer-save, deletion, completion, and admin-decrypt groups pass in this
  focused run.
- Remaining failures are concentrated in session-start integration tests.

### Category 1: `linkage_key_versions` seed is not visible to some tests

**Files still failing:**

- `tests/integration/core/test_flow_matrix.py`
- `tests/integration/core/test_session_start_response_contract.py`
- `tests/integration/core/test_transaction_boundary.py`

**Current failure:**

```text
ForeignKeyViolation: insert or update on table "submission_sessions" violates
foreign key constraint "submission_sessions_linkage_key_version_fkey"
DETAIL: Key (linkage_key_version)=(1) is not present in table "linkage_key_versions".
```

`tests/conftest.py` seeds `linkage_key_versions(version=1)` in
`core_db_session`, but these failing tests are not seeing that row at
`create_session()` time.

**What to do next:**

Verify which fixture path those tests use (`db_session`, `core_db_session`, or
`DbSessions`) and seed `linkage_key_versions(version=1)` on the same
transaction/session that `SessionStarter.start()` uses.

### Category 2: one session-start envelope mock misses linkage version

**File:** `tests/integration/core/test_session_start_envelope.py`

**Current failing test:**

`TestPreCommitEnvelopeFailureRollback.test_locator_failure_rolls_back_core_session`

**Current failure:**

```text
ProgrammingError: cannot adapt type 'MagicMock'
...
'linkage_key_version': <MagicMock name='mock.get_current_linkage_key_version()' ...>
```

The test creates a bare `MagicMock()` for `loc_svc` and sets
`for_new_session.side_effect`, but does not set
`get_current_linkage_key_version.return_value`. `SessionStarter` now reads that
version before calling `for_new_session`, so the mock itself reaches SQLAlchemy.

**What to do next:**

In that test, set:

```python
loc_svc.get_current_linkage_key_version.return_value = 1
```

before constructing `SessionStarter`.

---

## Not rechecked in this focused audit

### E2E module-level `SessionStarter` instance

The previous e2e note was not part of the focused command above. The old path
in that note is stale after the package split; if this still fails, patching
must target the current modules under
`app.services.public_submissions.core.actions` and
`app.services.public_submissions.core.shared`.

### Auth bootstrap and real AWS smoke tests

These remain outside this crypto-service integration checklist:

- `test_auth_bootstrap_service.py` tracks auth/project membership schema drift.
- `test_crypto_smoke.py` is expected to skip without real AWS encryption env
  vars.
