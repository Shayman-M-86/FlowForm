from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission_answer import SubmissionAnswer
from tests.integration.response.factories import make_submission, make_submission_answer

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_submission_answer_can_be_created(db_session: scoped_session[Session]) -> None:
    """All fields are persisted and the server default populates created_at."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(
        submission.id, question_key="q1", answer_family="field", answer_value={"value": "hi"}
    )
    db_session.add(answer)
    db_session.flush()

    saved = db_session.get(SubmissionAnswer, answer.id)
    assert saved is not None, "SubmissionAnswer was not persisted"
    assert saved.submission_id == submission.id, f"submission_id={saved.submission_id!r}, expected {submission.id!r}"
    assert saved.question_key == "q1", f"question_key={saved.question_key!r}, expected 'q1'"
    assert saved.answer_family == "field", f"answer_family={saved.answer_family!r}, expected 'field'"
    assert saved.answer_value == {"value": "hi"}, f"answer_value={saved.answer_value!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"


# ---------------------------------------------------------------------------
# NOT NULL constraints
# ---------------------------------------------------------------------------


def test_submission_answer_requires_question_key(db_session: scoped_session[Session]) -> None:
    """question_key is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(submission.id, question_key="q1")
    answer.question_key = None  # type: ignore[assignment]
    db_session.add(answer)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "question_key", (
        f"Expected NOT NULL violation on 'question_key', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_answer_requires_answer_family(db_session: scoped_session[Session]) -> None:
    """answer_family is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(submission.id, question_key="q1")
    answer.answer_family = None  # type: ignore[assignment]
    db_session.add(answer)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "answer_family", (
        f"Expected NOT NULL violation on 'answer_family', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Unique constraint
# ---------------------------------------------------------------------------


def test_submission_answer_unique_question_per_submission(db_session: scoped_session[Session]) -> None:
    """Two answers in the same submission cannot share a question_key."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_submission_answer(submission.id, question_key="q1", answer_value={"value": "first"})
    db_session.add(answer_a)
    db_session.flush()

    answer_b = make_submission_answer(submission.id, question_key="q1", answer_value={"value": "second"})
    db_session.add(answer_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_submission_answers_question", (
        f"Expected constraint 'uq_submission_answers_question', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_answer_same_key_allowed_across_submissions(db_session: scoped_session[Session]) -> None:
    """The same question_key may appear in different submissions."""
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


def test_submission_answer_different_keys_within_submission(db_session: scoped_session[Session]) -> None:
    """Multiple distinct question_keys are allowed within the same submission."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_submission_answer(submission.id, question_key="q1")
    answer_b = make_submission_answer(submission.id, question_key="q2")
    db_session.add_all([answer_a, answer_b])
    db_session.flush()

    saved = db_session.query(SubmissionAnswer).filter_by(submission_id=submission.id).all()
    assert len(saved) == 2, f"Expected 2 answers for submission {submission.id!r}, got {len(saved)}"


# ---------------------------------------------------------------------------
# answer_family CHECK constraint
# ---------------------------------------------------------------------------


def test_submission_answer_rejects_invalid_answer_family(db_session: scoped_session[Session]) -> None:
    """answer_family must be one of: choice, field, matching, rating."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(submission.id, question_key="q1", answer_family="text")
    db_session.add(answer)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_submission_answers_answer_family_valid", (
        f"Expected constraint 'ck_submission_answers_answer_family_valid', got '{constraint}'\n "
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


@pytest.mark.parametrize(
    "answer_family,answer_value",
    [
        ("choice", {"selected_option_ids": ["opt_a", "opt_b"]}),
        ("field", {"value": "hello"}),
        ("matching", {"pairs": [{"left_id": "x", "right_id": "y"}]}),
        ("rating", {"value": 4}),
    ],
)
def test_submission_answer_accepts_all_valid_families(
    db_session: scoped_session[Session],
    answer_family: str,
    answer_value: dict,
) -> None:
    """Each valid answer_family with a matching answer_value shape is accepted."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(
        submission.id, question_key="q1", answer_family=answer_family, answer_value=answer_value
    )
    db_session.add(answer)
    db_session.flush()

    saved = db_session.get(SubmissionAnswer, answer.id)
    assert saved is not None, f"SubmissionAnswer with answer_family={answer_family!r} was not persisted"
    assert saved.answer_family == answer_family, f"answer_family={saved.answer_family!r}, expected {answer_family!r}"


# ---------------------------------------------------------------------------
# answer_value shape CHECK constraints
# ---------------------------------------------------------------------------


def test_submission_answer_rejects_non_object_answer_value(db_session: scoped_session[Session]) -> None:
    """answer_value must be a JSON object — arrays and scalars are rejected."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(submission.id, question_key="q1")
    answer.answer_value = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(answer)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_submission_answers_answer_value_is_object", (
        f"Expected constraint 'ck_submission_answers_answer_value_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


@pytest.mark.parametrize(
    "answer_family,answer_value,expected_constraint",
    [
        (
            "choice",
            {"selected_option_ids": [1, 2]},  # integers are not a text array
            "ck_submission_answers_choice_shape_valid",
        ),
        (
            "field",
            {"value": {"nested": "obj"}},  # object is not scalar-or-null
            "ck_submission_answers_field_shape_valid",
        ),
        (
            "matching",
            {"pairs": [{"left": "a", "right": "b"}]},  # wrong keys — must be left_id / right_id
            "ck_submission_answers_matching_shape_valid",
        ),
        (
            "rating",
            {"value": "four"},  # string is not a number
            "ck_submission_answers_rating_shape_valid",
        ),
    ],
)
def test_submission_answer_rejects_invalid_shape(
    db_session: scoped_session[Session],
    answer_family: str,
    answer_value: dict,
    expected_constraint: str,
) -> None:
    """Each answer_family rejects an answer_value that doesn't match its required shape."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer = make_submission_answer(
        submission.id, question_key="q1", answer_family=answer_family, answer_value=answer_value
    )
    db_session.add(answer)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == expected_constraint, (
        f"Expected constraint '{expected_constraint}', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------


def test_submission_answer_accessible_via_relationship(db_session: scoped_session[Session]) -> None:
    """Answers added via the ORM relationship are correctly linked to the submission."""
    submission = make_submission()

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "field"
    answer.answer_value = {"value": 24}

    submission.answers.append(answer)
    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.answers) == 1, f"Expected 1 answer on submission, got {len(submission.answers)}"
    assert submission.answers[0].submission_id == submission.id, (
        f"answer.submission_id={submission.answers[0].submission_id!r}, expected {submission.id!r}"
    )
    assert submission.answers[0].question_key == "age", (
        f"answer.question_key={submission.answers[0].question_key!r}, expected 'age'"
    )
