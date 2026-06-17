## Pass report

Pass: 03 — AWS Wiring and Crypto Smoke Test

Changed files:
* `backend/pyproject.toml` — added `boto3>=1.38.0` dependency
* `backend/uv.lock` — regenerated with boto3 and transitive deps
* `backend/app/core/config.py` — added `EncryptionSettings` model and `encryption` field on `FlowForm`
* `backend/app/crypto/kms.py` — new: `wrap_dek`, `unwrap_dek` using boto3 KMS
* `backend/app/crypto/secrets.py` — new: `get_linkage_secret` using boto3 Secrets Manager
* `backend/app/crypto/dek_cache.py` — new: `DekCache` with TTL and eviction
* `backend/app/crypto/__init__.py` — updated re-exports for new modules
* `infra/docker/.backend.env` — renamed AWS vars to `FLOWFORM_ENCRYPTION_*` prefix

Behavior implemented:
* `wrap_dek` / `unwrap_dek` call real KMS encrypt/decrypt with encryption context
* `get_linkage_secret` fetches from Secrets Manager with optional `version_id` for rotation
* `DekCache` is a thread-safe worker-local cache keyed by session locator bytes with TTL, explicit eviction, and clear-all
* `EncryptionSettings` loads all AWS encryption config through pydantic-settings nested delimiter (`FLOWFORM_ENCRYPTION_*`)
* AWS credentials passed as `SecretStr` to prevent accidental logging

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "dek_cache"` — 10 passed
* `bash backend/scripts/run-tests.sh --ai -k "crypto_smoke"` — 2 passed
* `bash backend/scripts/run-tests.sh --ai -k "crypto"` — 39 passed
* `bash backend/scripts/run-tests.sh --ai` — 419 passed, 1 failed (pre-existing: `test_submission_session_response_omits_survey_schema_and_answers`)

Failures or skipped validation:
* 1 pre-existing failure in `tests/unit/test_submission_session_contracts.py::test_submission_session_response_omits_survey_schema_and_answers` — unrelated to this pass (survey schema field shape), last touched in commit `67b735b`.

Policy change during pass:
* Environment variable naming: all encryption env vars now use `FLOWFORM_ENCRYPTION_` prefix instead of bare `ENCRYPTION_*` / `AWS_*`. This aligns with the existing pydantic-settings `env_nested_delimiter="_"` convention used by all other `FLOWFORM_*` vars. Operator renamed vars in `.backend.env` accordingly.

Trace notes:
* entry points touched: none (no routes or services modified)
* service methods touched: none
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior: `test_dek_cache.py` (10 unit tests), `test_crypto_smoke.py` (2 integration tests)

Remaining risks:
* boto3 client is created per-call in `kms.py` and `secrets.py`. For production throughput, a shared client or session-scoped client may be needed. This is an optimisation for a later pass or post-MVP.
* `EncryptionSettings` is `Optional` on `FlowForm` — the app starts without encryption vars. Pass 04 should assert `settings.flowform.encryption is not None` at session-start time.

## Pass-forward

* `EncryptionSettings` lives at `settings.flowform.encryption` (type `EncryptionSettings | None`). Access via `current_settings().flowform.encryption`. Assert it's not `None` before use.
* `wrap_dek(plaintext_dek, key_arn, context, *, region, access_key_id, secret_access_key)` and `unwrap_dek(...)` require all AWS params explicitly — pull them from `EncryptionSettings`.
* `get_linkage_secret(secret_arn, version_id=None, *, region, access_key_id, secret_access_key)` returns raw 32-byte linkage secret.
* `DekCache` is instantiated per-worker. Cache key is `session_locator: bytes`. Call `cache.evict(session_locator)` on session complete/expire/abandon.
* All crypto imports available from `app.crypto`: `wrap_dek`, `unwrap_dek`, `get_linkage_secret`, `DekCache`, `KmsError`, `LinkageSecretError`.
* Error types: `KmsError` for KMS failures, `LinkageSecretError` for Secrets Manager failures. Both are plain `Exception` subclasses, not `AppError` — the service layer should catch and translate.
* AWS credentials are `SecretStr` on the settings model — call `.get_secret_value()` is handled inside `kms.py` / `secrets.py`; callers pass the `SecretStr` directly.
