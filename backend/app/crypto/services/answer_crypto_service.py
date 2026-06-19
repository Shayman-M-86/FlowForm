"""Service for encrypting and decrypting individual answer payloads.

AnswerCryptoService sits below the answer write/read workflow services and
above the low-level AES-GCM primitives. It turns structured answer fields
into encrypted bytes and reverses that process on read.

Encrypt path:
    1. Serialize (question_node_id, answer_state, answer_value) into a
       versioned JSON payload via ``build_plaintext_payload``.
    2. Generate a fresh 12-byte random nonce (unique per DEK usage).
    3. Encrypt with AES-256-GCM using the caller-supplied session DEK and
       AAD (additional authenticated data).
    4. Return ``EncryptedAnswer(ciphertext, nonce)`` for storage.

Decrypt path:
    1. Decrypt the stored ciphertext with the same DEK, nonce, and AAD.
       AES-GCM verifies integrity — any tampering or AAD mismatch raises
       ``DecryptionError``.
    2. Parse the plaintext back into structured fields.
    3. Return ``DecryptedAnswer(question_node_id, answer_state, answer_value)``.

AAD is treated as opaque bytes. The caller (typically a higher-level service)
is responsible for constructing it via ``build_aad``, which binds the
ciphertext to its session, submission, and question context. This prevents
answer-swapping attacks without this service needing to know about sessions
or locators.

This service does not call KMS, derive locators, query the database, or
validate survey answer rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.crypto.aes_gcm import decrypt_answer, encrypt_answer
from app.crypto.nonces import generate_nonce
from app.crypto.payload import build_plaintext_payload, parse_plaintext_payload

_PAYLOAD_VERSION = 1


@dataclass(frozen=True, slots=True)
class EncryptedAnswer:
    """The encrypted form of an answer payload."""

    ciphertext: bytes
    nonce: bytes


@dataclass(frozen=True, slots=True)
class DecryptedAnswer:
    """The decrypted and parsed answer payload."""

    question_node_id: str
    answer_state: str
    answer_value: Any


class AnswerCryptoService:
    """Encrypts and decrypts answer payloads using AES-256-GCM.

    Callers provide a plaintext session DEK and opaque AAD bytes.
    This service does not know about sessions, envelopes, locators,
    KMS, or databases.
    """

    def encrypt(
        self,
        dek: bytes,
        question_node_id: str,
        answer_state: str,
        answer_value: Any,
        aad: bytes,
    ) -> EncryptedAnswer:
        """Encrypt one answer payload. Generates a fresh nonce."""
        plaintext = build_plaintext_payload(
            _PAYLOAD_VERSION, question_node_id, answer_state, answer_value
        )
        nonce = generate_nonce()
        ciphertext = encrypt_answer(plaintext, dek, nonce, aad)
        return EncryptedAnswer(ciphertext=ciphertext, nonce=nonce)

    def decrypt(
        self,
        dek: bytes,
        ciphertext: bytes,
        nonce: bytes,
        aad: bytes,
    ) -> DecryptedAnswer:
        """Decrypt one stored answer payload."""
        raw = decrypt_answer(ciphertext, dek, nonce, aad)
        parsed = parse_plaintext_payload(raw)
        return DecryptedAnswer(
            question_node_id=parsed["question_node_id"],
            answer_state=parsed["answer_state"],
            answer_value=parsed["answer_value"],
        )
