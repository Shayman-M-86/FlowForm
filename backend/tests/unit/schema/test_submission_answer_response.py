"""Document-field answer request and response contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schema.api.requests.submission_sessions.answers import SaveSurveyDocumentAnswerRequest
from app.schema.api.responses.submission_sessions.answers import (
    SurveyDocumentAnswerResponse,
)


def test_cleared_answer_value_is_none() -> None:
    response = SurveyDocumentAnswerResponse(
        field_id="field_name",
        field_key="name",
        response_type="string",
        state="cleared",
        client_mutation_id=uuid4(),
        saved_at=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
    )
    assert response.model_dump(mode="json")["value"] is None


def test_survey_document_answer_response_uses_field_identity() -> None:
    response = SurveyDocumentAnswerResponse(
        field_id="field_consent",
        field_key="consent",
        response_type="choice",
        state="answered",
        value="option_yes",
        client_mutation_id=uuid4(),
        saved_at=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
    )

    dumped = response.model_dump(mode="json")
    assert dumped["field_id"] == "field_consent"
    assert dumped["response_type"] == "choice"
    assert dumped["value"] == "option_yes"


def test_survey_document_answer_request_does_not_accept_client_response_type() -> None:
    request = SaveSurveyDocumentAnswerRequest(
        client_mutation_id=uuid4(),
        state="answered",
        value="2026-06-18",
    )

    assert request.model_dump(mode="json")["value"] == "2026-06-18"
    assert "response_type" not in request.model_dump(mode="json")

    with pytest.raises(ValidationError):
        SaveSurveyDocumentAnswerRequest.model_validate(
            {
                "client_mutation_id": uuid4(),
                "state": "answered",
                "value": "3",
                "response_type": "integer",
            }
        )


def test_survey_document_clear_request_has_no_value() -> None:
    request = SaveSurveyDocumentAnswerRequest(
        client_mutation_id=uuid4(),
        state="cleared",
    )

    assert request.value is None


def test_answer_request_rejects_boolean_instead_of_coercing_it_to_a_number() -> None:
    with pytest.raises(ValidationError):
        SaveSurveyDocumentAnswerRequest(client_mutation_id=uuid4(), state="answered", value=True)
