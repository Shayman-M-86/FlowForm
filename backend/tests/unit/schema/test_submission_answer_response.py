"""Validate the saved field answer response variants at the HTTP boundary."""

from uuid import uuid4

from pydantic import TypeAdapter

from app.schema.api.responses.submission_sessions.answers import (
    SavedAnsweredResponse,
    SavedClearedResponse,
    SubmissionSessionAnswerResponse,
)

_RESPONSE = TypeAdapter(SubmissionSessionAnswerResponse)


def _metadata() -> dict[str, str]:
    return {
        "field_uuid": str(uuid4()),
        "client_mutation_id": str(uuid4()),
        "saved_at": "2026-06-18T12:00:00Z",
    }


def test_choice_set_serializes_option_uuids() -> None:
    raw = {
        **_metadata(),
        "state": "answered",
        "answer_spec": {"type": "choice_set", "required": True},
        "answer_value": [str(uuid4()), str(uuid4())],
    }
    response = _RESPONSE.validate_python(raw)
    assert isinstance(response, SavedAnsweredResponse)
    assert response.model_dump(mode="json", exclude_unset=True) == raw


def test_clear_serializes_without_a_value() -> None:
    raw = {**_metadata(), "state": "cleared"}
    response = _RESPONSE.validate_python(raw)
    assert isinstance(response, SavedClearedResponse)
    assert response.model_dump(mode="json", exclude_unset=True) == raw
