"""Tests for plaintext payload encode/decode."""

import pytest

from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload

_FIELD_ID = "field_health"


class TestBuildPlaintextPayload:
    def test_returns_bytes(self) -> None:
        result = build_plaintext_payload(
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        assert isinstance(result, bytes)

    def test_round_trip(self) -> None:
        payload = build_plaintext_payload(
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        parsed = parse_plaintext_payload(payload)
        assert parsed.field_id == _FIELD_ID
        assert parsed.answer_state == "answered"
        assert parsed.answer_value == {"value": "yes"}

    def test_none_value(self) -> None:
        payload = build_plaintext_payload(
            field_id=_FIELD_ID,
            answer_state="cleared",
            answer_value=None,
        )
        parsed = parse_plaintext_payload(payload)
        assert parsed.answer_value is None
        assert parsed.answer_state == "cleared"

    def test_complex_value(self) -> None:
        value = {"selected": [1, 2, 3], "nested": {"key": "val"}}
        payload = build_plaintext_payload(
            field_id=_FIELD_ID,
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
