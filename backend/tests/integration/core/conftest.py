from __future__ import annotations

from unittest.mock import MagicMock

import pytest  # type: ignore[import]
from sqlalchemy.orm import Session

from app.crypto.services import NewSessionDEK, NewSessionLocator
from app.schema.orm.core import Project, ProjectRole, ResponseStore, Survey, SurveyVersion, User
from tests.integration.core.factories import (
    make_project,
    make_project_role,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)


def _make_mock_locator_service():
    svc = MagicMock()
    svc.get_current_linkage_key_version.return_value = 1
    svc.for_new_session.return_value = NewSessionLocator(
        linkage_key_version=1, session_locator=b"\x00" * 32,
    )
    svc.for_existing_session.return_value = b"\x00" * 32
    svc.answer_locator.return_value = b"\x00" * 32
    return svc


def _make_mock_dek_service():
    svc = MagicMock()
    svc.create_for_session.return_value = NewSessionDEK(
        plaintext_dek=b"\x01" * 32, wrapped_session_dek=b"\x02" * 64,
    )
    svc.get_for_session.return_value = b"\x01" * 32
    return svc


def _make_mock_branch_key_service():
    svc = MagicMock()
    svc.get_plaintext_key.return_value = b"\x03" * 32
    svc.ensure_for_survey.return_value = MagicMock()
    return svc


@pytest.fixture(autouse=True)
def _mock_session_encryption(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-mock crypto services so existing core tests run without AWS."""
    from app.services.public_submissions.core.actions.session_starter import SessionStarter

    loc_svc = _make_mock_locator_service()
    dek_svc = _make_mock_dek_service()
    branch_key_svc = _make_mock_branch_key_service()

    fake_survey_key = MagicMock()
    monkeypatch.setattr(
        "app.services.public_submissions.core.actions.session_starter.load_survey_encryption_key",
        lambda *_args, **_kwargs: fake_survey_key,
    )
    monkeypatch.setattr(
        "app.services.public_submissions.core.shared.session_crypto.load_survey_encryption_key",
        lambda *_args, **_kwargs: fake_survey_key,
    )

    original_init = SessionStarter.__init__

    def patched_init(self, **kwargs):
        kwargs.setdefault("locator_service", loc_svc)
        kwargs.setdefault("dek_service", dek_svc)
        kwargs.setdefault("survey_branch_key_service", branch_key_svc)
        original_init(self, **kwargs)

    monkeypatch.setattr(SessionStarter, "__init__", patched_init)


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
