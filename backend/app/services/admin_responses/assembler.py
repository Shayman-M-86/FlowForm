"""Pure data transformation for admin response results.

Turns decrypted answer payloads and frozen question metadata into
API-facing result objects. No DB access — the service loads data,
the assembler shapes it.
"""
from __future__ import annotations

import logging
from typing import Any, cast, get_args
from uuid import UUID

from pydantic import ValidationError

from app.crypto import build_aad
from app.crypto.services import AnswerCryptoService
from app.crypto.services.answer_crypto_service import DecryptedAnswerPayload
from app.schema.api.submission_sessions.answer_payload import (
    SubmissionAnswerValue,
    parse_answer_value,
)
from app.schema.enums import AnswerFamily, QuestionFamily, SubmissionAnswerState
from app.schema.orm.core.survey_content import SurveyQuestion
from app.services.results import DecryptedAnswerResult

logger = logging.getLogger(__name__)

_QUESTION_FAMILIES: frozenset[str] = frozenset(get_args(QuestionFamily))

QuestionMetaMap = dict[UUID, tuple[str, AnswerFamily | None]]


def build_question_meta_map(
    question_nodes: list[SurveyQuestion],
) -> QuestionMetaMap:
    """Map each question node id to its (question_key, answer_family).

    The family is read from the frozen survey definition so decrypt can
    reconstruct it without storing it in the encrypted payload.
    """
    return {
        q.id: (q.question_key, _answer_family_from_schema(q.question_schema))
        for q in question_nodes
    }


def decrypt_revision(
    *,
    ciphertext: bytes,
    nonce: bytes,
    dek: bytes,
    crypto_version: int,
    envelope_id: UUID,
    answer_id: UUID,
    answer_locator: bytes,
    revision_id: UUID,
    revision_number: int,
    answer_crypto_service: AnswerCryptoService,
) -> DecryptedAnswerPayload:
    """Decrypt a single answer revision."""
    aad = build_aad(
        crypto_version=crypto_version,
        envelope_id=envelope_id,
        answer_id=answer_id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=revision_number,
    )
    return answer_crypto_service.decrypt(dek=dek, ciphertext=ciphertext, nonce=nonce, aad=aad)


def build_decrypted_answer_result(
    *,
    parsed: DecryptedAnswerPayload,
    question_meta_map: QuestionMetaMap,
    revision_number: int,
    revision_id: UUID,
) -> DecryptedAnswerResult:
    """Shape a decrypted payload into an API-facing result."""
    question_key, answer_family = question_meta_map.get(
        parsed.question_node_id, (None, None)
    )
    return DecryptedAnswerResult(
        question_node_id=parsed.question_node_id,
        question_key=question_key,
        answer_family=answer_family,
        answer_state=parsed.answer_state,
        answer_value=_resolve_answer_value(
            answer_family=answer_family,
            answer_state=parsed.answer_state,
            raw_value=parsed.answer_value,
        ),
        revision_number=revision_number,
        revision_id=revision_id,
    )


def _answer_family_from_schema(question_schema: object) -> AnswerFamily | None:
    """Read the top-level family discriminator from persisted question content."""
    if not isinstance(question_schema, dict):
        return None
    raw_family = question_schema.get("family")
    if raw_family not in _QUESTION_FAMILIES:
        return None
    return cast(AnswerFamily, raw_family)


def _resolve_answer_value(
    *,
    answer_family: AnswerFamily | None,
    answer_state: SubmissionAnswerState,
    raw_value: Any,
) -> SubmissionAnswerValue | dict[str, Any] | None:
    """Validate a decrypted raw value into a canonical model when possible.

    Falls back to the raw value (never raises) when the family is unknown or
    the stored value does not match the canonical shape.
    """
    if raw_value is None or answer_state == "cleared" or answer_family is None:
        return raw_value
    if not isinstance(raw_value, dict):
        return raw_value
    try:
        return parse_answer_value(answer_family, raw_value)
    except ValidationError:
        logger.warning(
            "Decrypted answer value did not match canonical %s shape; keeping raw value.",
            answer_family,
        )
        return raw_value
