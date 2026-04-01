from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import NotNullViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project
from app.models.core.response_store import ResponseStore
from app.models.core.survey import Survey, SurveyVersion
from app.models.core.survey_submission import SurveySubmission
from app.models.core.user import User


def test_survey_submission_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.survey_version_id = survey_version.id
    submission.response_store_id = response_store.id
    submission.submission_channel = "authenticated"
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False

    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(SurveySubmission, submission.id)
    assert saved is not None, "Submission was not persisted"
    assert saved.submitted_by_user_id == user.id, (
        f"submitted_by_user_id={saved.submitted_by_user_id!r}, expected {user.id!r}"
    )
    assert saved.submission_channel == "authenticated", (
        f"submission_channel={saved.submission_channel!r}, expected 'authenticated'"
    )
    assert saved.status == "pending", (
        f"status={saved.status!r}, expected 'pending'"
    )


def test_survey_submission_requires_survey_version(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    response_store: ResponseStore,
    user: User,
) -> None:
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.response_store_id = response_store.id
    submission.submission_channel = "authenticated"
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False

    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "survey_version_id", (
        f"Expected NOT NULL violation on 'survey_version_id', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_requires_submission_channel(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.survey_version_id = survey_version.id
    submission.response_store_id = response_store.id
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False

    db_session.add(submission)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "submission_channel", (
        f"Expected NOT NULL violation on 'submission_channel', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
