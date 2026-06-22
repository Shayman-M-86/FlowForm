"""Tests for plaintext payload encode/decode."""

from uuid import UUID

import pytest

from app.crypto.payload import PayloadDecodeError, build_plaintext_payload, parse_plaintext_payload

Q1 = UUID("00000000-0000-0000-0000-000000000001")
Q42 = UUID("00000000-0000-0000-0000-000000000042")


class TestPayloadRoundTrip:
    def test_basic_round_trip(self) -> None:
        raw = build_plaintext_payload(1, Q42, "answered", "yes")
        result = parse_plaintext_payload(raw)
        assert result == {
            "payload_version": 1,
            "question_node_id": Q42,
            "answer_state": "answered",
            "answer_value": "yes",
        }

    def test_cleared_state_round_trip(self) -> None:
        raw = build_plaintext_payload(1, Q42, "cleared", None)
        result = parse_plaintext_payload(raw)
        assert result["answer_state"] == "cleared"
        assert result["answer_value"] is None

    def test_complex_value_round_trip(self) -> None:
        value = {"choices": ["a", "b"], "other": "text"}
        raw = build_plaintext_payload(1, Q1, "answered", value)
        result = parse_plaintext_payload(raw)
        assert result["answer_value"] == value

    def test_numeric_value_round_trip(self) -> None:
        raw = build_plaintext_payload(1, Q1, "answered", 42)
        result = parse_plaintext_payload(raw)
        assert result["answer_value"] == 42


class TestPayloadDecodeErrors:
    def test_invalid_bytes(self) -> None:
        with pytest.raises(PayloadDecodeError, match="Invalid payload bytes"):
            parse_plaintext_payload(b"\xff\xfe")

    def test_missing_fields(self) -> None:
        with pytest.raises(PayloadDecodeError, match="Missing payload fields"):
            parse_plaintext_payload(b'{"v":1}')
