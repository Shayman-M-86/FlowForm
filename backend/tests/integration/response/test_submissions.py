from __future__ import annotations

import uuid
from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission import Submission
from tests.integration.response.factories import make_submission

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_submission_can_be_created(db_session: scoped_session[Session]) -> None:
    """All fields are persisted and server defaults populate submitted_at and created_at."""
    submission = make_submission(survey_id=10, survey_version_id=20, project_id=30)
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.core_submission_id == submission.core_submission_id, (
        f"core_submission_id={saved.core_submission_id!r}, expected {submission.core_submission_id!r}"
    )
    assert saved.survey_id == 10, f"survey_id={saved.survey_id!r}, expected 10"
    assert saved.survey_version_id == 20, f"survey_version_id={saved.survey_version_id!r}, expected 20"
    assert saved.project_id == 30, f"project_id={saved.project_id!r}, expected 30"
    assert saved.is_anonymous is False, f"is_anonymous={saved.is_anonymous!r}, expected False default"
    assert saved.submitted_at is not None, "submitted_at was not set by the server default"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_submission_is_anonymous_defaults_to_false(db_session: scoped_session[Session]) -> None:
    """is_anonymous defaults to False when not explicitly set."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.is_anonymous is False, f"is_anonymous={saved.is_anonymous!r}, expected False"


def test_submission_can_be_anonymous(db_session: scoped_session[Session]) -> None:
    """is_anonymous can be set to True."""
    submission = make_submission(is_anonymous=True)
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.is_anonymous is True, f"is_anonymous={saved.is_anonymous!r}, expected True"


def test_submission_can_have_pseudonymous_subject(db_session: scoped_session[Session]) -> None:
    """pseudonymous_subject_id accepts a UUID value."""
    subject_id = uuid.uuid4()
    submission = make_submission()
    submission.pseudonymous_subject_id = subject_id
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.pseudonymous_subject_id == subject_id, (
        f"pseudonymous_subject_id={saved.pseudonymous_subject_id!r}, expected {subject_id!r}"
    )


def test_submission_pseudonymous_subject_is_optional(db_session: scoped_session[Session]) -> None:
    """pseudonymous_subject_id is nullable — it defaults to None."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.pseudonymous_subject_id is None, (
        f"pseudonymous_subject_id={saved.pseudonymous_subject_id!r}, expected None"
    )


def test_submission_can_have_metadata(db_session: scoped_session[Session]) -> None:
    """submission_metadata accepts a JSON object."""
    submission = make_submission()
    submission.submission_metadata = {"source": "web", "version": 2}
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.submission_metadata == {"source": "web", "version": 2}, (
        f"submission_metadata={saved.submission_metadata!r}"
    )


def test_submission_metadata_is_optional(db_session: scoped_session[Session]) -> None:
    """submission_metadata is nullable — a submission can be created without it."""
    # Not assigning submission_metadata avoids psycopg3 sending Jsonb(None) for the JSONB column
    submission = Submission()
    submission.core_submission_id = 999_999_999
    submission.survey_id = 1
    submission.survey_version_id = 1
    submission.project_id = 1
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(Submission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.submission_metadata is None, f"submission_metadata={saved.submission_metadata!r}, expected None"


# ---------------------------------------------------------------------------
# NOT NULL constraints
# ---------------------------------------------------------------------------


def test_submission_requires_core_submission_id(db_session: scoped_session[Session]) -> None:
    """core_submission_id is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    submission.core_submission_id = None  # type: ignore[assignment]
    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "core_submission_id", (
        f"Expected NOT NULL violation on 'core_submission_id', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_requires_survey_id(db_session: scoped_session[Session]) -> None:
    """survey_id is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    submission.survey_id = None  # type: ignore[assignment]
    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "survey_id", (
        f"Expected NOT NULL violation on 'survey_id', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_requires_project_id(db_session: scoped_session[Session]) -> None:
    """project_id is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    submission.project_id = None  # type: ignore[assignment]
    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "project_id", (
        f"Expected NOT NULL violation on 'project_id', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Unique constraint
# ---------------------------------------------------------------------------


def test_submission_unique_core_submission_id(db_session: scoped_session[Session]) -> None:
    """core_submission_id must be globally unique — two submissions cannot share the same value."""
    submission_a = make_submission(core_submission_id=12345)
    db_session.add(submission_a)
    db_session.flush()

    submission_b = make_submission(core_submission_id=12345)
    db_session.add(submission_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "submissions_core_submission_id_key", (
        f"Expected constraint 'submissions_core_submission_id_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# metadata CHECK constraint
# ---------------------------------------------------------------------------


def test_submission_rejects_non_object_metadata(db_session: scoped_session[Session]) -> None:
    """submission_metadata must be a JSON object when set — arrays and scalars are rejected."""
    submission = make_submission()
    submission.submission_metadata = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_submissions_metadata_is_object", (
        f"Expected constraint 'ck_submissions_metadata_is_object', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()
