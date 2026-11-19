"""Self-describing field answers survive plaintext encoding without API metadata."""

import json

import pytest
from pydantic import TypeAdapter

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload
from app.schema.api.requests.submission_sessions import SaveSubmissionSessionAnswerRequest
from app.schema.models.survey_document.answers import AnswerData
from app.schema.types import SurveyFieldUuid

FIELD = TypeAdapter(SurveyFieldUuid).validate_python("00000000-0000-0000-0000-000000000001")
ANSWER = TypeAdapter(AnswerData)


@pytest.mark.parametrize(
    ("spec", "value"),
    [
        ({"type": "string", "required": True}, "yes"),
        ({"type": "integer", "required": True, "constraints": {"min": 1}}, 3),
        ({"type": "boolean", "required": True}, False),
        ({"type": "date", "required": True}, "2020-01-01"),
        ({"type": "choice_set", "required": True}, ["10000000-0000-4000-8000-000000000001"]),
    ],
)
def test_answered_payload_round_trip_keeps_specification(spec, value):
    answer = ANSWER.validate_python({"state": "answered", "answer_spec": spec, "answer_value": value})
    encoded = build_plaintext_payload(field_uuid=FIELD, answer=answer)
    parsed = parse_plaintext_payload(encoded)
    assert parsed.field_uuid == FIELD and parsed.state == "answered"
    assert parsed.answer_spec == answer.answer_spec
    assert json.loads(encoded)["answer_value"] == ANSWER.dump_python(answer, mode="json")["answer_value"]
    assert json.loads(encoded)["v"] == 2
    assert "question_node_id" not in json.loads(encoded)


def test_cleared_payload_has_no_answer_value():
    encoded = build_plaintext_payload(field_uuid=FIELD, answer=ANSWER.validate_python({"state": "cleared"}))
    assert parse_plaintext_payload(encoded).state == "cleared"
    assert "answer_value" not in json.loads(encoded)
    assert "answer_spec" not in json.loads(encoded)


def test_request_subclass_metadata_is_excluded():
    request = TypeAdapter(SaveSubmissionSessionAnswerRequest).validate_python(
        {
            "field_uuid": FIELD,
            "client_mutation_id": "20000000-0000-4000-8000-000000000001",
            "state": "answered",
            "answer_spec": {"type": "integer", "required": True},
            "answer_value": 3,
        }
    )
    raw = json.loads(build_plaintext_payload(field_uuid=FIELD, answer=request))
    assert "client_mutation_id" not in raw
    assert set(raw) == {"v", "field_uuid", "state", "answer_spec", "answer_value"}


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b'{"v":1,"question_node_id":"00000000-0000-0000-0000-000000000001",'
        b'"answer_state":"cleared","answer_value":null}',
        b'{"v":2,"field_uuid":"00000000-0000-0000-0000-000000000001","state":"answered"}',
    ],
)
def test_invalid_or_legacy_payload_is_not_reinterpreted(raw):
    with pytest.raises(PayloadDecodeError):
        parse_plaintext_payload(raw)


def test_unsupported_payload_version_is_rejected():
    raw = json.loads(build_plaintext_payload(field_uuid=FIELD, answer=ANSWER.validate_python({"state": "cleared"})))
    raw["v"] = 99
    with pytest.raises(PayloadDecodeError, match="Unsupported"):
        parse_plaintext_payload(json.dumps(raw).encode())
