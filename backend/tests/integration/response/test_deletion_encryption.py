"""Integration tests for response-first deletion.

Verifies:
- Full deletion removes response envelope then core session
- Deletion ordering: response DB first, then core
- Missing envelope raises EnvelopeNotFoundError
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.crypto.locators import derive_session_locator
from app.crypto.models import LinkageKey
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import response_envelope_repo
from app.services.admin_responses.service import AdminResponseService
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")

_ADMIN_SERVICE_MODULE = "app.services.admin_responses.service"


def _setup_core_fixtures(core_db: Session):
    user = make_user()
    core_db.add(user)
    core_db.flush()

    project = make_project(user_id=user.id)
    core_db.add(project)
    core_db.flush()

    store = make_response_store(project_id=project.id, user_id=user.id)
    core_db.add(store)
    core_db.flush()

    survey = make_survey(project_id=project.id, response_store_id=store.id, user_id=user.id)
    core_db.add(survey)
    core_db.flush()

    version = make_survey_version(survey_id=survey.id, user_id=user.id)
    core_db.add(version)
    core_db.flush()

    return project, survey, version


def _create_session_row(core_db: Session, project, survey, version):
    raw_token = "test-token-" + uuid.uuid4().hex[:8]
    session = create_session(
        core_db,
        project_id=project.id,
        survey_id=survey.id,
        survey_version_id=version.id,
        response_store_id=survey.default_response_store_id,
        link_id=None,
        project_subject_id=None,
        raw_browser_session_token=raw_token,
        linkage_key_version=1,
    )
    return session


class TestDeletion:
    def test_deletion_calls_response_delete_first(self, db_sessions: DbSessions) -> None:
        """Verify response-first ordering: delete_by_locator called before core delete."""
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)

        call_order: list[str] = []

        def mock_delete_by_locator(db, locator):
            call_order.append("response_delete")
            return True

        def mock_delete_session(db, *, submission_session):
            call_order.append("core_delete")

        def mock_commit(db, contexts):
            call_order.append("commit")

        with (
            patch(
                f"{_ADMIN_SERVICE_MODULE}.resolve_existing_session_locator",
                return_value=(loc.session_locator, _FAKE_LINKAGE_KEY),
            ),
            patch(
                f"{_ADMIN_SERVICE_MODULE}.response_envelope_repo.delete_by_locator",
                side_effect=mock_delete_by_locator,
            ),
            patch(
                f"{_ADMIN_SERVICE_MODULE}.ssr.delete_session",
                side_effect=mock_delete_session,
            ),
            patch(
                f"{_ADMIN_SERVICE_MODULE}.commit_with_err_handle",
                side_effect=mock_commit,
            ),
        ):
            service = AdminResponseService()
            result = service.delete_session(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        assert result.response_deleted is True
        assert result.core_deleted is True
        assert call_order.index("response_delete") < call_order.index("core_delete")

    def test_full_deletion_removes_envelope(self, db_sessions: DbSessions) -> None:
        """End-to-end: real DELETE on response DB, verify envelope is gone."""
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)
        session_locator = loc.session_locator
        wrapped_session_dek = os.urandom(64)

        response_envelope_repo.create(
            response_db,
            session_locator=session_locator,
            linkage_key_version=1,
            wrapped_session_dek=wrapped_session_dek,
            crypto_version=1,
        )

        with patch(
            f"{_ADMIN_SERVICE_MODULE}.resolve_existing_session_locator",
            return_value=(session_locator, _FAKE_LINKAGE_KEY),
        ):
            service = AdminResponseService()
            result = service.delete_session(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        assert result.response_deleted is True
        assert result.core_deleted is True
        assert response_envelope_repo.get_by_locator(response_db, session_locator) is None

    def test_missing_envelope_raises(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)

        with (
            patch(
                f"{_ADMIN_SERVICE_MODULE}.resolve_existing_session_locator",
                return_value=(loc.session_locator, _FAKE_LINKAGE_KEY),
            ),
            pytest.raises(EnvelopeNotFoundError),
        ):
            service = AdminResponseService()
            service.delete_session(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )
