from __future__ import annotations

import pytest
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
    assert saved is not None
    assert saved.submitted_by_user_id == user.id
    assert saved.submission_channel == "authenticated"
    assert saved.status == "pending"


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

    with pytest.raises(IntegrityError):
        db_session.flush()

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

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
