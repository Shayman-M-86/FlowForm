"""Encode and decode self-describing V2 field answers for encryption."""

from __future__ import annotations

from pydantic import TypeAdapter, ValidationError

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import PLAINTEXT_PAYLOAD_VERSION, PlaintextPayload
from app.schema.models.survey_document.answers import AnswerData
from app.schema.types import SurveyFieldUuid

_ANSWER = TypeAdapter(AnswerData)
_PAYLOAD = TypeAdapter(PlaintextPayload)


def build_plaintext_payload(*, field_uuid: SurveyFieldUuid, answer: AnswerData) -> bytes:
    """Serialize shared answer fields, excluding request-only subclass metadata."""
    data = _ANSWER.dump_python(answer, mode="json", exclude_none=True)
    payload = _PAYLOAD.validate_python({"v": PLAINTEXT_PAYLOAD_VERSION, "field_uuid": field_uuid, **data})
    return _PAYLOAD.dump_json(payload, by_alias=True, exclude_none=True)


def parse_plaintext_payload(raw: bytes) -> PlaintextPayload:
    """Parse a typed field answer and reject unsupported payload versions."""
    try:
        payload = _PAYLOAD.validate_json(raw)
    except ValidationError as exc:
        raise PayloadDecodeError("Invalid plaintext payload") from exc
    if payload.payload_version != PLAINTEXT_PAYLOAD_VERSION:
        raise PayloadDecodeError(f"Unsupported plaintext payload version: {payload.payload_version}")
    return payload
