from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest  # type: ignore[import]
from sqlalchemy.orm import Session

from app.crypto.models import (
    LinkageKey,
    NewSessionKey,
    NewSessionLocator,
    PlaintextSessionKey,
    SessionLocator,
    WrappedSessionKey,
)
from app.schema.orm.core import Project, ProjectRole, ResponseStore, Survey, SurveyVersion, User
from tests.integration.core.factories import (
    make_project,
    make_project_role,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=b"\xcc" * 32, aws_version_id="test-version")
_FAKE_SESSION_LOCATOR = SessionLocator(os.urandom(32))
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_FAKE_WRAPPED_DEK = WrappedSessionKey(b"\x02" * 64)

_STARTER_MODULE = "app.services.public_submissions.core.actions.session_starter"
_LOADER_MODULE = "app.services.public_submissions.core.session_loader"


@pytest.fixture(autouse=True)
def _mock_session_encryption(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-mock crypto module calls so existing core tests run without AWS."""
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.load_current_linkage_key",
        lambda _db: _FAKE_LINKAGE_KEY,
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.derive_session_locator",
        lambda _sid, _key: NewSessionLocator(
            linkage_key_version=1,
            session_locator=_FAKE_SESSION_LOCATOR,
        ),
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
        lambda _db, **_kw: MagicMock(return_value=os.urandom(32)),
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.create_session_key",
        lambda _ctx, _survey_key: NewSessionKey(
            plaintext_key=_FAKE_PLAINTEXT_DEK,
            wrapped_key=_FAKE_WRAPPED_DEK,
        ),
    )
    monkeypatch.setattr(
        f"{_LOADER_MODULE}.resolve_existing_session_locator",
        lambda _db, _sid, _ver: (_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
    )


@pytest.fixture
def user(db_session: Session) -> User:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def project(user: User, db_session: Session) -> Project:
    project = make_project(user.id)
    db_session.add(project)
    db_session.flush()
    return project


@pytest.fixture
def project_role(project: Project, db_session: Session) -> ProjectRole:
    role = make_project_role(project.id)
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def response_store(project: Project, user: User, db_session: Session) -> ResponseStore:
    store = make_response_store(project.id, user.id)
    db_session.add(store)
    db_session.flush()
    return store


@pytest.fixture
def survey(
    project: Project,
    response_store: ResponseStore,
    user: User,
    db_session: Session,
) -> Survey:
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()
    return survey


@pytest.fixture
def survey_version(survey: Survey, user: User, db_session: Session) -> SurveyVersion:
    version = make_survey_version(survey.id, user.id)
    db_session.add(version)
    db_session.flush()
    return version
