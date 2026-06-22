"""Versioned plaintext payload encode/decode for answer encryption.

This module is deliberately family-agnostic. The payload stores ``answer_value``
as the JSON form of a canonical ``SubmissionAnswerValue`` (see
``app.schema.api.submission_sessions.answer_payload``) but does NOT record which
question family it belongs to. The family is reconstructed from the survey
definition at decrypt time, so validating a decrypted value back into a typed
model is the decrypt service's job — this layer cannot know the family without
external context and so never parses ``answer_value`` beyond plain JSON.
"""

import json
from typing import Any, TypedDict, get_args
from uuid import UUID

from app.schema.enums import SubmissionAnswerState

PlaintextAnswerValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ParsedPlaintextPayload(TypedDict):
    """Typed structure decoded from one plaintext answer payload."""

    payload_version: int
    question_node_id: UUID
    answer_state: SubmissionAnswerState
    answer_value: PlaintextAnswerValue


_ANSWER_STATES: frozenset[str] = frozenset(get_args(SubmissionAnswerState))


class PayloadDecodeError(Exception):
    """Raised when a plaintext payload cannot be decoded."""


def build_plaintext_payload(
    payload_version: int,
    question_node_id: UUID,
    answer_state: SubmissionAnswerState,
    answer_value: PlaintextAnswerValue,
) -> bytes:
    """Encode a versioned plaintext payload for encryption."""
    payload = {
        "v": payload_version,
        "question_node_id": str(question_node_id),
        "answer_state": answer_state,
        "answer_value": answer_value,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_plaintext_payload(raw: bytes) -> ParsedPlaintextPayload:
    """Decode a versioned plaintext payload after decryption."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PayloadDecodeError("Invalid payload bytes") from exc

    if not isinstance(data, dict):
        raise PayloadDecodeError("Payload must be a JSON object")

    required_keys = {"v", "question_node_id", "answer_state", "answer_value"}
    missing = required_keys - set(data.keys())
    if missing:
        raise PayloadDecodeError(f"Missing payload fields: {sorted(missing)}")

    answer_state = data["answer_state"]
    if answer_state not in _ANSWER_STATES:
        raise PayloadDecodeError(f"Invalid answer_state: {answer_state!r}")

    return {
        "payload_version": data["v"],
        "question_node_id": UUID(data["question_node_id"]),
        "answer_state": answer_state,
        "answer_value": data["answer_value"],
    }
