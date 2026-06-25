"""Tests for plaintext payload encode/decode."""

from uuid import UUID

import pytest

from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload

_Q1 = UUID("00000000-0000-0000-0000-000000000001")


class TestBuildPlaintextPayload:
    def test_returns_bytes(self) -> None:
        result = build_plaintext_payload(
            question_node_id=_Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        assert isinstance(result, bytes)

    def test_round_trip(self) -> None:
        payload = build_plaintext_payload(
            question_node_id=_Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        parsed = parse_plaintext_payload(payload)
        assert parsed.question_node_id == _Q1
        assert parsed.answer_state == "answered"
        assert parsed.answer_value == {"value": "yes"}

    def test_none_value(self) -> None:
        payload = build_plaintext_payload(
            question_node_id=_Q1,
            answer_state="cleared",
            answer_value=None,
        )
        parsed = parse_plaintext_payload(payload)
        assert parsed.answer_value is None
        assert parsed.answer_state == "cleared"

    def test_complex_value(self) -> None:
        value = {"selected": [1, 2, 3], "nested": {"key": "val"}}
        payload = build_plaintext_payload(
            question_node_id=_Q1,
            answer_state="answered",
            answer_value=value,
        )
        parsed = parse_plaintext_payload(payload)
        assert parsed.answer_value == value


class TestParsePlaintextPayload:
    def test_invalid_json_raises(self) -> None:
        from app.crypto._internal.errors import PayloadDecodeError

        with pytest.raises(PayloadDecodeError):
            parse_plaintext_payload(b"not valid json")
