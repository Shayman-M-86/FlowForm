"""Encode/decode versioned plaintext answer payloads for encryption.

This layer is deliberately family-agnostic.

The encrypted payload stores ``answer_value`` as plain JSON. Its trusted
``field_id`` identifies the response contract in the frozen survey definition.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import (
    PLAINTEXT_PAYLOAD_VERSION,
    PlaintextAnswerValue,
    PlaintextPayload,
    PlaintextPayloadInput,
)
from app.schema.api.content.common import FieldId
from app.schema.enums import SubmissionAnswerState


def build_plaintext_payload(
    *,
    field_id: FieldId,
    answer_state: SubmissionAnswerState,
    answer_value: PlaintextAnswerValue,
) -> bytes:
    """Build the current plaintext payload bytes for encryption."""
    payload = PlaintextPayloadInput(
        payload_version=PLAINTEXT_PAYLOAD_VERSION,
        field_id=field_id,
        answer_state=answer_state,
        answer_value=answer_value,
    ).to_plaintext_payload()

    return payload.model_dump_json(by_alias=True).encode("utf-8")


def parse_plaintext_payload(raw: bytes) -> PlaintextPayload:
    """Parse decrypted plaintext bytes into the canonical payload model."""
    try:
        payload = PlaintextPayload.model_validate_json(raw)
    except ValidationError as exc:
        raise PayloadDecodeError("Invalid plaintext payload") from exc

    if payload.payload_version != PLAINTEXT_PAYLOAD_VERSION:
        raise PayloadDecodeError(f"Unsupported plaintext payload version: {payload.payload_version}")
    return payload
