# Pass 01: Crypto Helpers

## Goal

Implement the pure cryptographic building blocks that every later pass depends on.
No database access, no AWS — all in-memory computation.

## Files to create

- `backend/app/crypto/__init__.py`
- `backend/app/crypto/locators.py` — session and answer locator derivation
- `backend/app/crypto/aes_gcm.py` — AES-256-GCM encrypt and decrypt
- `backend/app/crypto/payload.py` — versioned plaintext payload encode/decode
- `backend/app/crypto/aad.py` — AAD construction for answer revisions
- `backend/app/crypto/nonces.py` — fresh nonce generation

## In scope

- `derive_session_locator(core_session_id: str, linkage_secret: bytes) -> bytes` — HMAC-SHA256
- `derive_answer_locator(core_session_id: str, question_node_id: str, linkage_secret: bytes) -> bytes` — HMAC-SHA256 over `"<session_id>:<question_node_id>"`
- `encrypt_answer(plaintext: bytes, dek: bytes, nonce: bytes, aad: bytes) -> bytes`
- `decrypt_answer(ciphertext: bytes, dek: bytes, nonce: bytes, aad: bytes) -> bytes` — raises on AAD mismatch or tampered ciphertext
- `build_aad(crypto_version: int, envelope_id: int, answer_id: int, answer_locator: bytes, revision_id: int, revision_number: int) -> bytes`
- `build_plaintext_payload(payload_version: int, question_node_id: str, answer_state: str, answer_value: Any | None) -> bytes`
- `parse_plaintext_payload(raw: bytes) -> dict`
- `generate_nonce() -> bytes` — 12 bytes, cryptographically random

## Decisions locked by source docs

- Locator derivation uses HMAC-SHA256 (doc 02)
- Cipher is AES-256-GCM (doc 05)
- Nonce is 96-bit (12 bytes); reuse with the same DEK is a serious bug (doc 05)
- AAD fields in order: crypto_version, envelope_id, answer_id, answer_locator, revision_id, revision_number (doc 05)
- Plaintext payload fields: payload_version, question_node_id, answer_state, answer_value — null when cleared (doc 05)
- Every answer must be encrypted including cleared states (doc 05)

## Out of scope

- KMS, Secrets Manager, DEK wrapping — pass 03
- Database access of any kind
- Flask wiring or config

## Done when

- [ ] All functions implemented with full type hints, mypy clean
- [ ] Unit tests cover: locator determinism, session locator ≠ answer locator for same inputs, encrypt→decrypt round-trip, AAD mismatch raises, nonce uniqueness across 1000 calls, payload encode→decode round-trip, cleared-state payload round-trip
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "crypto"`

## Dependencies

None — this is pass 01.
