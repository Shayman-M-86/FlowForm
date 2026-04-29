from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, scoped_session

from app.core.errors import AppError
from app.repositories import surveys_repo
from app.schema.api.requests.submissions.answers import FieldAnswerIn, FieldAnswerValue
from app.schema.api.requests.submissions.create import SlugSubmissionRequest
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyScoringRule
from app.services.submissions import SubmissionIntakeService
from app.services.surveys import SurveyService
from tests.integration.conftest import DbSessions
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_question,
    make_survey_rule,
    make_survey_scoring_rule,
    make_survey_version,
    make_user,
)


def test_archive_active_published_version_unpublishes_and_archives(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Lifecycle Project", slug="lifecycle-project")
    db_session.add(project)
    db_session.flush()

    store = make_response_store(project.id, user.id, name="primary")
    db_session.add(store)
    db_session.flush()

    survey = make_survey(project.id, store.id, user.id, title="Lifecycle Survey")
    db_session.add(survey)
    db_session.flush()

    published_at = datetime(2024, 1, 1, tzinfo=UTC)
    version = make_survey_version(survey.id, user.id, version_number=1, status="published")
    version.compiled_schema = {"questions": []}
    version.published_at = published_at
    db_session.add(version)
    db_session.flush()

    survey.published_version_id = version.id
    db_session.flush()

    service = SurveyService()
    archived = SurveyService.archive_version.__wrapped__(
        service,
        db=db_session,
        project_id=project.id,
        survey_id=survey.id,
        version_number=1,
        actor=user,
    )

    db_session.refresh(survey)
    db_session.refresh(archived)

    assert survey.published_version_id is None
    assert archived.status == "archived"
    assert archived.published_at == published_at


def test_publish_new_version_archives_previous_live_version_in_safe_order(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Republish Project", slug="republish-project")
    db_session.add(project)
    db_session.flush()

    store = make_response_store(project.id, user.id, name="primary")
    db_session.add(store)
    db_session.flush()

    survey = make_survey(project.id, store.id, user.id, title="Republish Survey")
    db_session.add(survey)
    db_session.flush()

    current = make_survey_version(survey.id, user.id, version_number=1, status="published")
    current.compiled_schema = {"questions": [{"id": 1}]}
    current.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(current)
    db_session.flush()

    survey.published_version_id = current.id
    db_session.flush()

    draft = make_survey_version(survey.id, user.id, version_number=2, status="draft")
    db_session.add(draft)
    db_session.flush()

    question = make_survey_question(draft.id, question_key="q1")
    db_session.add(question)
    db_session.flush()

    service = SurveyService()
    published = SurveyService.publish_version.__wrapped__(
        service,
        db=db_session,
        project_id=project.id,
        survey_id=survey.id,
        version_number=2,
        actor=user,
    )

    db_session.refresh(survey)
    db_session.refresh(current)
    db_session.refresh(published)

    assert survey.published_version_id == published.id
    assert current.status == "archived"
    assert published.status == "published"
    assert published.published_at is not None


def test_copy_version_to_draft_clones_content_and_creates_new_version_number(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Copy Project", slug="copy-project")
    db_session.add(project)
    db_session.flush()

    store = make_response_store(project.id, user.id, name="primary")
    db_session.add(store)
    db_session.flush()

    survey = make_survey(project.id, store.id, user.id, title="Copy Survey")
    db_session.add(survey)
    db_session.flush()

    source = make_survey_version(survey.id, user.id, version_number=2, status="archived")
    source.compiled_schema = {"questions": [{"id": 1}]}
    source.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(source)
    db_session.flush()

    db_session.add(make_survey_question(source.id, question_key="q1"))
    db_session.add(make_survey_rule(source.id, rule_key="r1"))
    db_session.add(make_survey_scoring_rule(source.id, scoring_key="s1"))
    db_session.flush()

    service = SurveyService()
    draft = SurveyService.copy_version_to_draft.__wrapped__(
        service,
        db=db_session,
        project_id=project.id,
        survey_id=survey.id,
        version_number=2,
        actor=user,
    )

    assert draft.version_number == 3
    assert draft.status == "draft"
    assert draft.id != source.id

    cloned_version = surveys_repo.get_version(db_session, project.id, survey.id, 3)
    assert cloned_version is not None

    copied_questions = list(
        db_session.scalars(
            select(SurveyQuestion).where(
                SurveyQuestion.survey_version_id == draft.id,
                SurveyQuestion.node_type == "question",
            )
        )
    )
    copied_rules = list(
        db_session.scalars(
            select(SurveyQuestion).where(
                SurveyQuestion.survey_version_id == draft.id,
                SurveyQuestion.node_type == "rule",
            )
        )
    )
    copied_scoring_rules = list(
        db_session.scalars(select(SurveyScoringRule).where(SurveyScoringRule.survey_version_id == draft.id))
    )

    assert len(copied_questions) == 1
    assert copied_questions[0].question_key == "q1"
    assert len(copied_rules) == 1
    assert copied_rules[0].question_key == "r1"
    assert len(copied_scoring_rules) == 1
    assert copied_scoring_rules[0].scoring_key == "s1"


def test_unpublished_survey_rejects_submission_after_unpublish(
    db_sessions: DbSessions,
) -> None:
    core_db = db_sessions.core
    response_db = db_sessions.response

    user = make_user(auth0_user_id="auth0|submit-blocked", email="submit-blocked@example.com")
    core_db.add(user)
    core_db.flush()

    project = make_project(user.id, name="Submit Project", slug="submit-project")
    core_db.add(project)
    core_db.flush()

    store = make_response_store(project.id, user.id, name="primary")
    core_db.add(store)
    core_db.flush()

    survey = make_survey(project.id, store.id, user.id, title="Submit Survey")
    survey.visibility = "public"
    survey.public_slug = "submit-survey"
    core_db.add(survey)
    core_db.flush()

    version = make_survey_version(survey.id, user.id, version_number=1, status="published")
    version.compiled_schema = {"questions": [{"id": 1, "question_key": "q1"}]}
    version.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    core_db.add(version)
    core_db.flush()

    survey.published_version_id = version.id
    core_db.flush()

    service = SurveyService()
    SurveyService.archive_version.__wrapped__(
        service,
        db=core_db,
        project_id=project.id,
        survey_id=survey.id,
        version_number=1,
        actor=user,
    )

    submission_service = SubmissionIntakeService()
    payload = SlugSubmissionRequest(
        public_slug=survey.public_slug,
        survey_version_id=version.id,
        answers=[
            FieldAnswerIn(
                question_key="q1",
                answer_family="field",
                answer_value=FieldAnswerValue(value="test"),
            )
        ],
    )

    with pytest.raises(AppError) as exc_info:
        submission_service.create_slug_submission(
            core_db,
            response_db,
            payload=payload,
            submitted_by_user_id=user.id,
        )

    assert exc_info.value.code == "SURVEY_NOT_PUBLISHED"


def test_direct_active_archive_trigger_translates_to_app_error_not_key_error(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Trigger Project", slug="trigger-project")
    db_session.add(project)
    db_session.flush()

    store = make_response_store(project.id, user.id, name="primary")
    db_session.add(store)
    db_session.flush()

    survey = make_survey(project.id, store.id, user.id, title="Trigger Survey")
    db_session.add(survey)
    db_session.flush()

    version = make_survey_version(survey.id, user.id, version_number=1, status="published")
    version.compiled_schema = {"questions": []}
    version.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(version)
    db_session.flush()

    survey.published_version_id = version.id
    db_session.flush()

    with pytest.raises(AppError) as exc_info:
        surveys_repo.archive_version(db_session, version)

    assert exc_info.value.code == "VERSION_STATE_PROTECTED"
    assert "Published version id=" in exc_info.value.message
