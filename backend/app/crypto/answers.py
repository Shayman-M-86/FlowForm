"""Answer payload encryption and decryption."""

from __future__ import annotations

from uuid import UUID

from app.crypto._internal.aad import build_aad
from app.crypto._internal.models import (
    DecryptedAnswerPayload,
    EncryptedAnswerPayload,
    PlaintextAnswerValue,
)
from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload
from app.crypto._internal.wrapping import decrypt_answer, encrypt_answer
from app.crypto.locators import derive_answer_locator
from app.crypto.models import (
    AnswerLocator,
    RevisionContext,
    SessionContext,
)
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState

AnswerValueInput = SubmissionAnswerValue | PlaintextAnswerValue


def derive_session_answer_locator(
    context: SessionContext,
    question_node_id: UUID,
) -> AnswerLocator:
    """Derive the response-side answer locator for a session/question pair."""
    return derive_answer_locator(
        context.session_id,
        question_node_id,
        context.linkage_key,
    )


def encrypt_answer_revision(
    *,
    context: RevisionContext,
    question_node_id: UUID,
    answer_state: SubmissionAnswerState,
    answer_value: AnswerValueInput,
) -> EncryptedAnswerPayload:
    """Encrypt a new answer revision before storing it.

    Called during public submission when a respondent saves or updates
    an answer. Serialises the answer into a plaintext payload, generates
    a fresh nonce, and encrypts with AES-256-GCM using AAD derived from
    the revision context.
    """
    aad = build_aad(context)
    plaintext = build_plaintext_payload(
        question_node_id=question_node_id,
        answer_state=answer_state,
        answer_value=answer_value,
    )
    nonce = generate_nonce()
    ciphertext = encrypt_answer(plaintext, context.dek, nonce, aad)
    return EncryptedAnswerPayload(ciphertext=ciphertext, nonce=nonce)


def decrypt_answer_revision(
    *,
    ciphertext: bytes,
    nonce: bytes,
    context: RevisionContext,
) -> DecryptedAnswerPayload:
    """Decrypt a stored answer revision for admin viewing."""
    aad = build_aad(context)
    raw = decrypt_answer(ciphertext, context.dek, nonce, aad)
    parsed = parse_plaintext_payload(raw)

    return DecryptedAnswerPayload(
        question_node_id=parsed.question_node_id,
        answer_state=parsed.answer_state,
        answer_value=parsed.answer_value,
    )
