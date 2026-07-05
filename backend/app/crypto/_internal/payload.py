"""Encode/decode versioned plaintext answer payloads for encryption.

This layer is deliberately family-agnostic.

The encrypted payload stores ``answer_value`` as plain JSON. It does not record
the question family. The decrypt service must use the survey definition to
reconstruct and validate the typed answer model.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import (
    PLAINTEXT_PAYLOAD_VERSION,
    PlaintextAnswerValue,
    PlaintextPayload,
    PlaintextPayloadInput,
)
from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import SubmissionAnswerState


def build_plaintext_payload(
    *,
    question_node_id: UUID,
    answer_state: SubmissionAnswerState,
    answer_value: SubmissionAnswerValue | PlaintextAnswerValue,
) -> bytes:
    """Build the current plaintext payload bytes for encryption."""
    payload = PlaintextPayloadInput(
        payload_version=PLAINTEXT_PAYLOAD_VERSION,
        question_node_id=question_node_id,
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
