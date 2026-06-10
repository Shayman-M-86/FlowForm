from uuid import UUID

import pytest
from pydantic import ValidationError

from app.openapi.export import _build_minimal_spec_app
from app.openapi.spec import build_spec
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
)


def test_start_submission_session_accepts_public_slug_access() -> None:
    payload = StartSubmissionSessionRequest.model_validate(
        {
            "access": {
                "type": "public_slug",
                "public_slug": "customer-intake",
            }
        }
    )

    assert payload.access.type == "public_slug"
    assert payload.access.public_slug == "customer-intake"


def test_start_submission_session_rejects_legacy_submission_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        StartSubmissionSessionRequest.model_validate(
            {
                "access": {
                    "type": "public_slug",
                    "public_slug": "customer-intake",
                },
                "survey_version_id": 31,
                "started_at": "2026-06-11T01:20:00Z",
                "submitted_at": "2026-06-11T01:31:00Z",
                "answers": [],
                "metadata": {},
            }
        )

    fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert {"survey_version_id", "started_at", "submitted_at", "answers", "metadata"} <= fields


def test_save_answer_rejects_body_question_identifier() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
                "answer_family": "rating",
                "answer_value": {"value": 8},
            }
        )

    assert exc_info.value.errors()[0]["loc"] == ("question_node_id",)


def test_save_answer_requires_answer_payload_when_answered() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
            }
        )

    assert "answer_family is required" in exc_info.value.errors()[0]["msg"]


def test_clear_answer_forbids_answer_payload() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "b10063cb-9fb4-4ac2-b399-769f8781127f",
                "state": "cleared",
                "answer_family": "rating",
                "answer_value": {"value": 8},
            }
        )

    assert "answer_family must be omitted" in exc_info.value.errors()[0]["msg"]


def test_submission_session_paths_are_in_openapi_spec() -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)
    paths = spec["paths"]

    assert sorted(paths["/api/v1/public/links/resolve"]) == ["post"]
    assert "post" in paths["/api/v1/public/submission-sessions"]
    assert "get" in paths["/api/v1/public/submission-sessions/current"]
    assert "put" in paths["/api/v1/public/submission-sessions/current/answers/{question_node_id}"]
    assert "post" in paths["/api/v1/public/submission-sessions/current/events/question-viewed"]
    assert "post" in paths["/api/v1/public/submission-sessions/current/complete"]


def test_save_answer_accepts_client_mutation_uuid() -> None:
    payload = SaveSubmissionSessionAnswerRequest.model_validate(
        {
            "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
            "state": "answered",
            "answer_family": "rating",
            "answer_value": {"value": 8},
        }
    )

    assert payload.client_mutation_id == UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31")
