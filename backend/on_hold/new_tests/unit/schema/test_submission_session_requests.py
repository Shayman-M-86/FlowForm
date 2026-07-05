"""Unit tests for respondent submission-session request schemas."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schema.api import limits
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)


def test_start_submission_session_accepts_public_slug_access() -> None:
    """Public slug access should parse as the public-slug variant."""
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


def test_start_submission_session_accepts_link_token_access() -> None:
    """Link token access should parse as the link-token variant."""
    payload = StartSubmissionSessionRequest.model_validate(
        {
            "access": {
                "type": "link_token",
                "token": "tok_test_123",
            }
        }
    )

    assert payload.access.type == "link_token"
    assert payload.access.token == "tok_test_123"


def test_start_submission_session_rejects_legacy_submission_fields() -> None:
    """Session start should not accept legacy submission-create fields."""
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


def test_start_submission_session_rejects_bad_slug() -> None:
    """Public slug access should enforce the canonical slug format."""
    with pytest.raises(ValidationError):
        StartSubmissionSessionRequest.model_validate(
            {
                "access": {
                    "type": "public_slug",
                    "public_slug": "Bad Slug",
                }
            }
        )


def test_start_submission_session_rejects_blank_link_token() -> None:
    """Link token access should reject blank tokens."""
    with pytest.raises(ValidationError):
        StartSubmissionSessionRequest.model_validate(
            {
                "access": {
                    "type": "link_token",
                    "token": "  ",
                }
            }
        )


def test_start_submission_session_enforces_token_size_limit() -> None:
    """Link tokens should use the shared token length limit."""
    with pytest.raises(ValidationError):
        StartSubmissionSessionRequest.model_validate(
            {
                "access": {
                    "type": "link_token",
                    "token": "x" * (limits.TOKEN_MAX + 1),
                }
            }
        )


def test_save_answer_accepts_client_mutation_uuid() -> None:
    """Answer-save requests should parse client mutation IDs as UUIDs."""
    payload = SaveSubmissionSessionAnswerRequest.model_validate(
        {
            "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
            "state": "answered",
            "answer_family": "rating",
            "answer_value": {"variant": "slider", "number": 8},
        }
    )

    assert payload.client_mutation_id == UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31")


def test_save_answer_requires_answer_payload_when_answered() -> None:
    """Answered state requires both answer family and answer value."""
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
            }
        )

    assert "answer_family is required" in exc_info.value.errors()[0]["msg"]


def test_save_answer_rejects_family_value_mismatch() -> None:
    """The declared answer family must match the nested answer payload."""
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
                "answer_family": "choice",
                "answer_value": {"variant": "slider", "number": 8},
            }
        )

    assert "answer_value must be a choice answer" in exc_info.value.errors()[0]["msg"]


def test_clear_answer_forbids_answer_payload() -> None:
    """Cleared state must not carry stale answer payload data."""
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "b10063cb-9fb4-4ac2-b399-769f8781127f",
                "state": "cleared",
                "answer_family": "rating",
                "answer_value": {"variant": "slider", "number": 8},
            }
        )

    assert "answer_family must be omitted" in exc_info.value.errors()[0]["msg"]


def test_save_answer_rejects_body_question_identifier() -> None:
    """The question ID belongs in the route, not the answer-save request body."""
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
                "answer_family": "rating",
                "answer_value": {"variant": "slider", "number": 8},
            }
        )

    assert exc_info.value.errors()[0]["loc"] == ("question_node_id",)


def test_submission_session_event_accepts_question_viewed_event() -> None:
    """Question-viewed events should parse their question UUID."""
    payload = SubmissionSessionEventRequest.model_validate(
        {
            "event_type": "question_viewed",
            "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
        }
    )

    assert payload.event_type == "question_viewed"
    assert payload.question_node_id == UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539")


def test_submission_session_event_rejects_unknown_event_type() -> None:
    """Event type should stay within the known respondent event enum."""
    with pytest.raises(ValidationError):
        SubmissionSessionEventRequest.model_validate(
            {
                "event_type": cast(Any, "not_an_event"),
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
            }
        )
