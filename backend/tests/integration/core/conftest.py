from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core import Project, ProjectRole, ResponseStore, Survey, SurveyVersion, User
from tests.integration.core.factories import (
    make_project,
    make_project_role,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)


@pytest.fixture
def user(db_session: scoped_session[Session]) -> User:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def project(user: User, db_session: scoped_session[Session]) -> Project:
    project = make_project(user.id)
    db_session.add(project)
    db_session.flush()
    return project


@pytest.fixture
def project_role(project: Project, db_session: scoped_session[Session]) -> ProjectRole:
    role = make_project_role(project.id)
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def response_store(project: Project, user: User, db_session: scoped_session[Session]) -> ResponseStore:
    store = make_response_store(project.id, user.id)
    db_session.add(store)
    db_session.flush()
    return store


@pytest.fixture
def survey(
    project: Project,
    response_store: ResponseStore,
    user: User,
    db_session: scoped_session[Session],
) -> Survey:
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()
    return survey


@pytest.fixture
def survey_version(survey: Survey, user: User, db_session: scoped_session[Session]) -> SurveyVersion:
    version = make_survey_version(survey.id, user.id)
    db_session.add(version)
    db_session.flush()
    return version
