"""Field-answer payload encryption and decryption."""

from __future__ import annotations

from uuid import UUID

from app.crypto._internal.aad import build_aad
from app.crypto._internal.models import DecryptedAnswerPayload, EncryptedAnswerPayload
from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload
from app.crypto._internal.wrapping import decrypt_answer, encrypt_answer
from app.crypto.locators import derive_answer_locator
from app.crypto.models import AnswerContext, AnswerLocator, LinkageKey
from app.schema.models.survey_document.answers import AnswerData
from app.schema.types import SurveyFieldUuid


def derive_slot_answer_locator(slot_id: UUID, linkage_key: LinkageKey) -> AnswerLocator:
    """Derive the stable response locator from the core slot identity."""
    return derive_answer_locator(slot_id, linkage_key)


def encrypt_answer_current(
    *, context: AnswerContext, field_uuid: SurveyFieldUuid, answer: AnswerData
) -> EncryptedAnswerPayload:
    """Encrypt the field identity and shared answered/cleared data with fresh nonce."""
    plaintext = build_plaintext_payload(field_uuid=field_uuid, answer=answer)
    nonce = generate_nonce()
    ciphertext = encrypt_answer(plaintext, context.dek, nonce, build_aad(context))
    return EncryptedAnswerPayload(ciphertext=ciphertext, nonce=nonce)


def decrypt_answer_current(*, ciphertext: bytes, nonce: bytes, context: AnswerContext) -> DecryptedAnswerPayload:
    """Decrypt a stored V2 field answer using its unchanged database-bound AAD."""
    raw = decrypt_answer(ciphertext, context.dek, nonce, build_aad(context))
    return parse_plaintext_payload(raw)
