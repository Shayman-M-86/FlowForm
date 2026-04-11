from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, scoped_session

from app.repositories import projects_repo
from app.repositories.response_stores_repo import (
    DEFAULT_PLATFORM_RESPONSE_STORE_CONNECTION_REFERENCE,
    DEFAULT_PLATFORM_RESPONSE_STORE_NAME,
)
from app.schema.api.requests.projects import CreateProjectRequest
from app.schema.api.requests.surveys import CreateSurveyRequest
from app.schema.orm.core.response_store import ResponseStore
from app.services.surveys import SurveyService
from tests.integration.core.factories import make_project, make_survey, make_survey_question, make_survey_version


def test_create_project_bootstraps_platform_primary_response_store(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = projects_repo.create_project(
        db_session,
        CreateProjectRequest(name="Bootstrap Project", slug="bootstrap-project"),
        created_by_user_id=user.id,
    )
    db_session.flush()

    stores = list(
        db_session.scalars(
            select(ResponseStore).where(ResponseStore.project_id == project.id)
        )
    )
    assert len(stores) == 1

    store = stores[0]
    assert store.name == DEFAULT_PLATFORM_RESPONSE_STORE_NAME
    assert store.store_type == "platform_postgres"
    assert store.connection_reference == DEFAULT_PLATFORM_RESPONSE_STORE_CONNECTION_REFERENCE
    assert store.is_active is True
    assert store.created_by_user_id == user.id


def test_create_survey_backfills_missing_project_response_store(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Legacy Project", slug="legacy-project")
    db_session.add(project)
    db_session.flush()

    service = SurveyService()
    survey = SurveyService.create_survey.__wrapped__(
        service,
        db=db_session,
        project_id=project.id,
        data=CreateSurveyRequest(title="Survey Without Store"),
        actor=user,
    )

    store = db_session.scalar(
        select(ResponseStore).where(ResponseStore.project_id == project.id)
    )
    assert store is not None
    assert survey.default_response_store_id == store.id
    assert store.name == DEFAULT_PLATFORM_RESPONSE_STORE_NAME


def test_publish_version_backfills_missing_survey_response_store(
    db_session: scoped_session[Session],
    user,
) -> None:
    project = make_project(user.id, name="Publish Project", slug="publish-project")
    db_session.add(project)
    db_session.flush()

    survey = make_survey(project.id, response_store_id=0, user_id=user.id, title="Legacy Survey")
    survey.default_response_store_id = None
    db_session.add(survey)
    db_session.flush()

    version = make_survey_version(survey.id, user.id, version_number=1, status="draft")
    db_session.add(version)
    db_session.flush()

    question = make_survey_question(version.id, question_key="q1")
    db_session.add(question)
    db_session.flush()

    service = SurveyService()
    published = SurveyService.publish_version.__wrapped__(
        service,
        db=db_session,
        project_id=project.id,
        survey_id=survey.id,
        version_number=1,
        actor=user,
    )

    db_session.refresh(survey)
    db_session.refresh(published)

    store = db_session.scalar(
        select(ResponseStore).where(ResponseStore.project_id == project.id)
    )
    assert store is not None
    assert survey.default_response_store_id == store.id
    assert published.status == "published"
