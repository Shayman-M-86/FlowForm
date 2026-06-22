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
    4. Return ``EncryptedAnswerPayload(ciphertext, nonce)`` for storage.

Decrypt path:
    1. Decrypt the stored ciphertext with the same DEK, nonce, and AAD.
       AES-GCM verifies integrity — any tampering or AAD mismatch raises
       ``DecryptionError``.
    2. Parse the plaintext back into structured fields.
    3. Return ``DecryptedAnswerPayload(question_node_id, answer_state, answer_value)``.

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
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel

from app.crypto.aes_gcm import decrypt_answer, encrypt_answer
from app.crypto.nonces import generate_nonce
from app.crypto.payload import (
    PlaintextAnswerValue,
    build_plaintext_payload,
    parse_plaintext_payload,
)
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState

_PAYLOAD_VERSION = 1

AnswerValueInput = SubmissionAnswerValue | dict[str, Any] | None
DecryptedAnswerValue = PlaintextAnswerValue


@dataclass(frozen=True, slots=True)
class EncryptedAnswerPayload:
    """Ciphertext and nonce for one encrypted answer plaintext payload."""

    ciphertext: bytes
    nonce: bytes


@dataclass(frozen=True, slots=True)
class DecryptedAnswerPayload:
    """Parsed plaintext fields recovered from one decrypted answer payload."""

    question_node_id: UUID
    answer_state: SubmissionAnswerState
    answer_value: DecryptedAnswerValue


EncryptedAnswer = EncryptedAnswerPayload
DecryptedAnswer = DecryptedAnswerPayload


class AnswerCryptoService:
    """Encrypts and decrypts answer payloads using AES-256-GCM.

    Callers provide a plaintext session DEK and opaque AAD bytes.
    This service does not know about sessions, envelopes, locators,
    KMS, or databases.
    """

    def encrypt(
        self,
        dek: bytes,
        question_node_id: UUID,
        answer_state: SubmissionAnswerState,
        answer_value: AnswerValueInput,
        aad: bytes,
    ) -> EncryptedAnswerPayload:
        """Encrypt one answer payload. Generates a fresh nonce."""
        plaintext = build_plaintext_payload(
            _PAYLOAD_VERSION,
            question_node_id,
            answer_state,
            _answer_value_to_json(answer_value),
        )
        nonce = generate_nonce()
        ciphertext = encrypt_answer(plaintext, dek, nonce, aad)
        return EncryptedAnswerPayload(ciphertext=ciphertext, nonce=nonce)

    def decrypt(
        self,
        dek: bytes,
        ciphertext: bytes,
        nonce: bytes,
        aad: bytes,
    ) -> DecryptedAnswerPayload:
        """Decrypt one stored answer payload."""
        raw = decrypt_answer(ciphertext, dek, nonce, aad)
        parsed = parse_plaintext_payload(raw)
        return DecryptedAnswerPayload(
            question_node_id=parsed["question_node_id"],
            answer_state=parsed["answer_state"],
            answer_value=parsed["answer_value"],
        )


def _answer_value_to_json(answer_value: AnswerValueInput) -> dict[str, Any] | None:
    if answer_value is None:
        return None
    if isinstance(answer_value, BaseModel):
        return cast(dict[str, Any], answer_value.model_dump(mode="json"))
    return answer_value
