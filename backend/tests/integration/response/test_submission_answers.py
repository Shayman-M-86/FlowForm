from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission_answer import SubmissionAnswer
from tests.integration.response.factories import make_submission, make_submission_answer


def test_submission_answer_unique_question_per_submission(db_session: scoped_session[Session]) -> None:

    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_family="field",
        answer_value={"value": "hello"},
    )
    db_session.add(answer_a)
    db_session.flush()

    answer_b = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_family="field",
        answer_value={"value": "again"},
    )
    db_session.add(answer_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_submission_answers_question", (
        f"Expected constraint 'uq_submission_answers_question', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_allows_different_question_keys_within_same_submission(
    db_session: scoped_session[Session],
) -> None:
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_submission_answer(submission.id, question_key="q1")
    answer_b = make_submission_answer(submission.id, question_key="q2")

    db_session.add_all([answer_a, answer_b])
    db_session.flush()

    saved_answers = db_session.query(SubmissionAnswer).filter_by(submission_id=submission.id).all()
    assert len(saved_answers) == 2, (
        f"Expected 2 answers for submission {submission.id}, got {len(saved_answers)}"
    )


def test_submission_allows_same_question_key_across_different_submissions(
    db_session: scoped_session[Session],
) -> None:
    submission_a = make_submission()
    submission_b = make_submission()
    db_session.add_all([submission_a, submission_b])
    db_session.flush()

    answer_a = make_submission_answer(submission_a.id, question_key="q1")
    answer_b = make_submission_answer(submission_b.id, question_key="q1")

    db_session.add_all([answer_a, answer_b])
    db_session.flush()

    assert answer_a.submission_id != answer_b.submission_id, (
        f"Both answers share submission_id={answer_a.submission_id!r}; expected different submissions"
    )


def test_submission_relationships_answers_work(db_session: scoped_session[Session]) -> None:
    submission = make_submission()

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "field"
    answer.answer_value = {"value": 24}

    submission.answers.append(answer)

    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.answers) == 1, (
        f"Expected 1 answer on submission, got {len(submission.answers)}"
    )
    assert submission.answers[0].submission_id == submission.id, (
        f"answer.submission_id={submission.answers[0].submission_id!r}, expected {submission.id!r}"
    )
    assert submission.answers[0].question_key == "age", (
        f"answer.question_key={submission.answers[0].question_key!r}, expected 'age'"
    )
