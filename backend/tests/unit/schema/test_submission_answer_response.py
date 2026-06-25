"""Unit tests for the typed SubmissionSessionAnswerResponse.

Confirms the typed ``answer_value`` serializes to the same JSON shape the
respondent route previously produced from a raw dict, and accepts both a
canonical model and a None (cleared) value.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.schema.api.responses.submission_sessions.answers import SubmissionSessionAnswerResponse
from app.schema.api.submission_sessions.answer_payload import ChoiceAnswerValue


def test_typed_answer_value_serializes_to_expected_json() -> None:
    node_id = uuid4()
    mutation_id = uuid4()
    saved = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    response = SubmissionSessionAnswerResponse(
        question_node_id=node_id,
        node_key="question-1",
        state="answered",
        answer_family="choice",
        answer_value=ChoiceAnswerValue(selected=["o1", "o2"]),
        revision_number=1,
        client_mutation_id=mutation_id,
        saved_at=saved,
    )

    dumped = response.model_dump(mode="json")
    assert dumped["node_key"] == "question-1"
    assert dumped["answer_family"] == "choice"
    assert dumped["answer_value"] == {"selected": ["o1", "o2"]}
    assert dumped["state"] == "answered"
    assert dumped["revision_number"] == 1


def test_cleared_answer_value_is_none() -> None:
    response = SubmissionSessionAnswerResponse(
        question_node_id=uuid4(),
        node_key="question-1",
        state="cleared",
        answer_family=None,
        answer_value=None,
        revision_number=2,
        client_mutation_id=uuid4(),
        saved_at=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
    )

    dumped = response.model_dump(mode="json")
    assert dumped["answer_value"] is None
    assert dumped["answer_family"] is None
