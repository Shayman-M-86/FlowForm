"""Unit tests for respondent submission-session response schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.schema.api.responses.submission_sessions import (
    CompleteSubmissionSessionResponse,
    StartSubmissionSessionResponse,
    SubmissionSessionAnswerResponse,
)


def test_start_response_contains_only_acknowledgement_fields() -> None:
    """Session start response should not inline the survey schema or answers."""
    current = datetime.now(UTC)
    response = StartSubmissionSessionResponse(
        status="in_progress",
        started_at=current,
        expires_at=current,
        survey_version_id=31,
        subject_code="sub_test",
    )

    dumped = response.model_dump(mode="json")

    assert dumped == {
        "status": "in_progress",
        "started_at": current.isoformat().replace("+00:00", "Z"),
        "expires_at": current.isoformat().replace("+00:00", "Z"),
        "survey_version_id": 31,
        "subject_code": "sub_test",
    }
    assert "survey_schema" not in dumped
    assert "survey" not in dumped
    assert "version" not in dumped
    assert "compiled_schema" not in dumped
    assert "answers" not in dumped


def test_answer_response_serializes_canonical_answer_value() -> None:
    """Latest-answer responses should carry the canonical nested answer payload."""
    current = datetime.now(UTC)
    response = SubmissionSessionAnswerResponse.model_validate(
        {
            "question_node_id": UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539"),
            "node_key": "q_customer_satisfaction",
            "state": "answered",
            "answer_family": "rating",
            "answer_value": {"variant": "slider", "number": 8},
            "client_mutation_id": UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31"),
            "saved_at": current,
        }
    )

    dumped = response.model_dump(mode="json")

    assert dumped["question_node_id"] == "771ab5a1-462c-4c98-8fe5-dbc2c1939539"
    assert dumped["node_key"] == "q_customer_satisfaction"
    assert dumped["state"] == "answered"
    assert dumped["answer_family"] == "rating"
    assert dumped["answer_value"] == {"variant": "slider", "number": 8.0}
    assert dumped["client_mutation_id"] == "ce823b7d-5295-4ca6-bbb8-cfe367f28b31"
    assert dumped["saved_at"] == current.isoformat().replace("+00:00", "Z")


def test_answer_response_serializes_cleared_answer() -> None:
    """Cleared-answer responses should omit answer family and value."""
    current = datetime.now(UTC)
    response = SubmissionSessionAnswerResponse(
        question_node_id=UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539"),
        node_key="q_customer_satisfaction",
        state="cleared",
        answer_family=None,
        answer_value=None,
        client_mutation_id=UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31"),
        saved_at=current,
    )

    dumped = response.model_dump(mode="json")

    assert dumped["state"] == "cleared"
    assert dumped["answer_family"] is None
    assert dumped["answer_value"] is None


def test_completion_response_serializes_completion_timestamp() -> None:
    """Completion response should acknowledge completed state and timestamp."""
    current = datetime.now(UTC)
    response = CompleteSubmissionSessionResponse(status="completed", completed_at=current)

    assert response.model_dump(mode="json") == {
        "status": "completed",
        "completed_at": current.isoformat().replace("+00:00", "Z"),
    }
