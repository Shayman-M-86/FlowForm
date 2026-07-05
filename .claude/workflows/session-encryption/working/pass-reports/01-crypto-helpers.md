## Pass report

Pass: 01 — crypto-helpers

Changed files:
* `backend/app/crypto/__init__.py` (created)
* `backend/app/crypto/locators.py` (created)
* `backend/app/crypto/aes_gcm.py` (created)
* `backend/app/crypto/payload.py` (created)
* `backend/app/crypto/aad.py` (created)
* `backend/app/crypto/nonces.py` (created)
* `backend/tests/unit/crypto/__init__.py` (created)
* `backend/tests/unit/crypto/test_locators.py` (created)
* `backend/tests/unit/crypto/test_aes_gcm.py` (created)
* `backend/tests/unit/crypto/test_payload.py` (created)
* `backend/tests/unit/crypto/test_aad.py` (created)
* `backend/tests/unit/crypto/test_nonces.py` (created)

Behavior implemented:
* `derive_session_locator(core_session_id, linkage_secret) -> bytes` — HMAC-SHA256 over session ID
* `derive_answer_locator(core_session_id, question_node_id, linkage_secret) -> bytes` — HMAC-SHA256 over `"<session_id>:<question_node_id>"`
* `encrypt_answer(plaintext, dek, nonce, aad) -> bytes` — AES-256-GCM encryption with 32-byte DEK validation
* `decrypt_answer(ciphertext, dek, nonce, aad) -> bytes` — AES-256-GCM decryption; raises `DecryptionError` on failure
* `build_aad(crypto_version, envelope_id, answer_id, answer_locator, revision_id, revision_number) -> bytes` — struct-packed canonical AAD
* `build_plaintext_payload(payload_version, question_node_id, answer_state, answer_value) -> bytes` — JSON-encoded versioned payload
* `parse_plaintext_payload(raw) -> dict` — decode with field validation; raises `PayloadDecodeError`
* `generate_nonce() -> bytes` — 12-byte `os.urandom`

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "crypto"` — 28 passed

Failures or skipped validation:
* none

Policy change during pass:
* none

Trace notes:
* entry points touched: none (pure library code)
* service methods touched: none
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: n/a
* tests that now describe behavior: `test_locators.py`, `test_aes_gcm.py`, `test_payload.py`, `test_aad.py`, `test_nonces.py`

Remaining risks:
* none

## Pass-forward

* Crypto package lives at `backend/app/crypto/`; `__init__.py` re-exports all public functions.
* Locator functions: `derive_session_locator(core_session_id: str, linkage_secret: bytes) -> bytes` and `derive_answer_locator(core_session_id: str, question_node_id: str, linkage_secret: bytes) -> bytes`.
* AAD: `build_aad(crypto_version, envelope_id, answer_id, answer_locator, revision_id, revision_number) -> bytes` — uses `struct.pack` with length-prefixed locator. All int args except `revision_number` (plain int) are packed as 64-bit for envelope_id, answer_id, revision_id.
* Payload: `build_plaintext_payload` returns sorted-key compact JSON bytes; `parse_plaintext_payload` returns dict with key `payload_version` (mapped from `v`).
* Encrypt/decrypt: `encrypt_answer`/`decrypt_answer` require 32-byte DEK; decrypt raises `DecryptionError` (not bare Exception).
* Nonces: `generate_nonce()` returns 12 bytes via `os.urandom`.
* `PayloadDecodeError` and `DecryptionError` are the two error types exported.
