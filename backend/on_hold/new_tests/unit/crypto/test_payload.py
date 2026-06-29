"""Contract tests for plaintext answer payload encoding."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import pytest

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import PLAINTEXT_PAYLOAD_VERSION
from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload

QUESTION_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_plaintext_payload_round_trips_answered_value() -> None:
    """Answered payloads should preserve question ID, state, and JSON answer value."""
    answer_value = {"selected": ["option-1", "option-2"]}

    payload = build_plaintext_payload(
        question_node_id=QUESTION_ID,
        answer_state="answered",
        answer_value=cast(Any, answer_value),
    )
    parsed = parse_plaintext_payload(payload)

    assert isinstance(payload, bytes)
    assert parsed.payload_version == PLAINTEXT_PAYLOAD_VERSION
    assert parsed.question_node_id == QUESTION_ID
    assert parsed.answer_state == "answered"
    assert parsed.answer_value == answer_value


def test_plaintext_payload_round_trips_cleared_value() -> None:
    """Cleared payloads should preserve a null answer value."""
    payload = build_plaintext_payload(
        question_node_id=QUESTION_ID,
        answer_state="cleared",
        answer_value=None,
    )
    parsed = parse_plaintext_payload(payload)

    assert parsed.question_node_id == QUESTION_ID
    assert parsed.answer_state == "cleared"
    assert parsed.answer_value is None


def test_plaintext_payload_accepts_nested_json_value() -> None:
    """Payload encoding should preserve JSON-compatible nested answer data."""
    answer_value = {"selected": [1, 2, 3], "nested": {"key": "value"}}

    payload = build_plaintext_payload(
        question_node_id=QUESTION_ID,
        answer_state="answered",
        answer_value=cast(Any, answer_value),
    )

    assert parse_plaintext_payload(payload).answer_value == answer_value


def test_parse_plaintext_payload_rejects_invalid_json() -> None:
    """Malformed decrypted bytes should become a payload decode error."""
    with pytest.raises(PayloadDecodeError):
        parse_plaintext_payload(b"not valid json")


def test_parse_plaintext_payload_rejects_unsupported_payload_version() -> None:
    """Payload version is part of the stable plaintext contract."""
    raw = json.dumps(
        {
            "v": PLAINTEXT_PAYLOAD_VERSION + 1,
            "question_node_id": str(QUESTION_ID),
            "answer_state": "answered",
            "answer_value": {"selected": ["option-1"]},
        }
    ).encode("utf-8")

    with pytest.raises(PayloadDecodeError):
        parse_plaintext_payload(raw)
