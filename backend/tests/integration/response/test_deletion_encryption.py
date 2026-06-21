"""Integration tests for response-first deletion.

Verifies:
- Full deletion removes response envelope then core session
- Deletion ordering: response DB first, then core
- Partial deletion (core fails) raises DeletionPendingError
- Missing envelope raises EnvelopeNotFoundError
"""
from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import derive_session_locator
from app.domain.errors import DeletionPendingError, EnvelopeNotFoundError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import response_envelope_repo
from app.services.public_submissions.core.deletion import delete_session_responses
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
_FAKE_ENC_SETTINGS = EncryptionSettings(
    kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
    linkage_secret_arn="arn:aws:secretsmanager:us-east-1:000000000000:secret:test",
    aws_region="us-east-1",
    aws_access_key_id=SecretStr("AKIAIOSFODNN7EXAMPLE"),
    aws_secret_access_key=SecretStr("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
)


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

    survey = make_survey(
        project_id=project.id, response_store_id=store.id, user_id=user.id
    )
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


def _patch_deletion_crypto():
    return patch(
        "app.services.public_submissions.core.deletion.get_linkage_secret",
        return_value=_LINKAGE_SECRET,
    )


class TestDeletion:

    def test_deletion_calls_response_delete_first(self, db_sessions: DbSessions) -> None:
        """Verify response-first ordering: delete_by_locator called before core delete."""
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        call_order: list[str] = []

        def mock_delete_by_locator(db, locator):
            call_order.append("response_delete")
            return True

        def mock_commit(db, contexts):
            call_order.append("commit")

        with (
            _patch_deletion_crypto(),
            patch(
                "app.services.public_submissions.core.deletion.response_envelope_repo.delete_by_locator",
                side_effect=mock_delete_by_locator,
            ),
            patch(
                "app.services.public_submissions.core.deletion.commit_with_err_handle",
                side_effect=mock_commit,
            ),
        ):
            # Mock db.delete to avoid actually deleting the session
            with patch.object(core_db, "delete") as mock_core_delete:
                mock_core_delete.side_effect = lambda s: call_order.append("core_delete")
                result = delete_session_responses(
                    core_db, response_db,
                    session=session,
                    encryption_settings=_FAKE_ENC_SETTINGS,
                )

        assert result.response_deleted is True
        assert result.core_deleted is True
        assert result.pending is False
        assert call_order.index("response_delete") < call_order.index("core_delete")

    def test_core_delete_failure_marks_pending(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        commit_count = [0]

        def mock_commit(db, contexts):
            commit_count[0] += 1
            if commit_count[0] == 2:
                raise Exception("Core commit failed")

        with (
            _patch_deletion_crypto(),
            patch(
                "app.services.public_submissions.core.deletion.response_envelope_repo.delete_by_locator",
                return_value=True,
            ),
            patch(
                "app.services.public_submissions.core.deletion.commit_with_err_handle",
                side_effect=mock_commit,
            ),
            pytest.raises(DeletionPendingError),
        ):
            delete_session_responses(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )

    def test_full_deletion_removes_envelope(self, db_sessions: DbSessions) -> None:
        """End-to-end: real DELETE on response DB, verify envelope is gone."""
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        session_locator = derive_session_locator(str(session.id), _LINKAGE_SECRET)
        response_envelope_repo.create(
            response_db,
            session_locator=session_locator,
            linkage_key_version=1,
            wrapped_dek=os.urandom(64),
            kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
            kms_context_version=1,
            crypto_version=1,
        )

        with _patch_deletion_crypto():
            result = delete_session_responses(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )

        assert result.response_deleted is True
        assert result.core_deleted is True
        assert result.pending is False
        assert response_envelope_repo.get_by_locator(response_db, session_locator) is None

    def test_missing_envelope_raises(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version = _setup_core_fixtures(core_db)
        session = _create_session_row(core_db, project, survey, version)

        with _patch_deletion_crypto(), pytest.raises(EnvelopeNotFoundError):
            delete_session_responses(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )
