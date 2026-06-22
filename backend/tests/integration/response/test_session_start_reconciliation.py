"""Integration tests for session-start reconciliation repair.

Verifies that:
- In-progress committed core session with no response envelope is marked abandoned
- In-progress committed core session with a matching envelope stays in_progress
- Completed and already-abandoned sessions are ignored
- A repaired abandoned session is rejected by the current-session loader
- Normal KMS/envelope failure still asserts rollback, not abandoned
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto.errors import KmsError
from app.crypto.services import NewSessionDEK, NewSessionLocator
from app.domain.errors import SessionInvalidError, SessionStartError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.reconciliation import (
    reconcile_orphaned_sessions,
)
from app.services.public_submissions.core.shared.session_loader import load_current_session
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_SCHEMA = {"nodes": [{"id": "q1", "type": "short_text"}]}
_FAKE_SESSION_LOCATOR = os.urandom(32)
_FAKE_PLAINTEXT_DEK = os.urandom(32)
_FAKE_WRAPPED_DEK = b"\xbb" * 64
_FAKE_ENC_SETTINGS = EncryptionSettings(
    kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
    linkage_secret_arn="arn:aws:secretsmanager:us-east-1:000000000000:secret:test",
    aws_region="us-east-1",
    aws_access_key_id=SecretStr("AKIAIOSFODNN7EXAMPLE"),
    aws_secret_access_key=SecretStr("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
)


def _seed_published_survey(db: Session, slug: str) -> int:
    user = make_user()
    db.add(user)
    db.flush()

    project = make_project(user.id)
    db.add(project)
    db.flush()

    store = make_response_store(project.id, user.id)
    db.add(store)
    db.flush()

    survey = make_survey(project.id, store.id, user.id)
    survey.visibility = "public"
    survey.public_slug = slug
    db.add(survey)
    db.flush()

    version = make_survey_version(survey.id, user.id)
    version.status = "published"
    version.compiled_schema = _SCHEMA
    version.published_at = datetime.now(UTC)
    db.add(version)
    db.flush()

    survey.published_version_id = version.id
    db.flush()

    return survey.id


def _slug_payload(slug: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": slug}}
    )


def _mock_locator_service(session_locator: bytes | None = None):
    svc = MagicMock()
    loc_bytes = session_locator or _FAKE_SESSION_LOCATOR
    svc.get_current_linkage_key_version.return_value = 1
    svc.for_new_session.return_value = NewSessionLocator(
        linkage_key_version=1,
        session_locator=loc_bytes,
    )
    svc.for_existing_session.return_value = loc_bytes
    return svc


def _mock_dek_service(
    plaintext_dek: bytes | None = None,
    wrapped_dek: bytes | None = None,
):
    svc = MagicMock()
    svc.create_for_session.return_value = NewSessionDEK(
        plaintext_dek=plaintext_dek or _FAKE_PLAINTEXT_DEK,
        wrapped_dek=wrapped_dek or _FAKE_WRAPPED_DEK,
    )
    return svc


def _start_session(
    db_sessions: DbSessions,
    slug: str,
    *,
    locator_service: MagicMock | None = None,
) -> tuple[SubmissionSession, str, MagicMock]:
    """Start a full session (core + response envelope) and return the session, token, and locator service."""
    loc_svc = locator_service or _mock_locator_service()
    starter = SessionStarter(
        locator_service=loc_svc,
        dek_service=_mock_dek_service(),
        encryption_settings=_FAKE_ENC_SETTINGS,
    )
    _, browser_token, _ = starter.start(
        db_sessions.core,
        db_sessions.response,
        payload=_slug_payload(slug),
        actor=None,
    )
    session = db_sessions.core.scalar(
        select(SubmissionSession).order_by(SubmissionSession.started_at.desc())
    )
    assert session is not None
    return session, browser_token, loc_svc


class TestReconcileOrphanedSessions:
    def test_in_progress_without_envelope_is_marked_abandoned(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "recon-orphan")
        loc_svc = _mock_locator_service()

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        _, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("recon-orphan"),
            actor=None,
        )

        # Delete the response envelope to simulate the orphan state
        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        db_sessions.response.delete(envelope)
        db_sessions.response.commit()

        result = reconcile_orphaned_sessions(
            db_sessions.core,
            db_sessions.response,
            encryption_settings=_FAKE_ENC_SETTINGS,
            locator_service=loc_svc,
        )

        assert result.abandoned == 1
        assert result.matched == 0

        session = db_sessions.core.scalar(select(SubmissionSession))
        assert session is not None
        assert session.session_status == "abandoned"

    def test_in_progress_with_matching_envelope_stays_in_progress(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "recon-match")
        loc_svc = _mock_locator_service()

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("recon-match"),
            actor=None,
        )

        result = reconcile_orphaned_sessions(
            db_sessions.core,
            db_sessions.response,
            encryption_settings=_FAKE_ENC_SETTINGS,
            locator_service=loc_svc,
        )

        assert result.matched == 1
        assert result.abandoned == 0

        session = db_sessions.core.scalar(select(SubmissionSession))
        assert session is not None
        assert session.session_status == "in_progress"

    def test_completed_session_is_ignored(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "recon-completed")
        loc_svc = _mock_locator_service()

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("recon-completed"),
            actor=None,
        )

        session = db_sessions.core.scalar(select(SubmissionSession))
        assert session is not None
        now = datetime.now(UTC)
        session.session_status = "completed"
        session.completed_at = now
        session.last_activity_at = now
        db_sessions.core.flush()
        db_sessions.core.commit()

        result = reconcile_orphaned_sessions(
            db_sessions.core,
            db_sessions.response,
            encryption_settings=_FAKE_ENC_SETTINGS,
            locator_service=loc_svc,
        )

        assert result.scanned == 0
        assert result.abandoned == 0

    def test_already_abandoned_session_is_ignored(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "recon-abandoned")
        loc_svc = _mock_locator_service()

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("recon-abandoned"),
            actor=None,
        )

        session = db_sessions.core.scalar(select(SubmissionSession))
        assert session is not None
        session.session_status = "abandoned"
        db_sessions.core.flush()
        db_sessions.core.commit()

        result = reconcile_orphaned_sessions(
            db_sessions.core,
            db_sessions.response,
            encryption_settings=_FAKE_ENC_SETTINGS,
            locator_service=loc_svc,
        )

        assert result.scanned == 0
        assert result.abandoned == 0


class TestAbandonedSessionRejectedByLoader:
    def test_loader_rejects_abandoned_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "recon-reject")
        loc_svc = _mock_locator_service()

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        _, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("recon-reject"),
            actor=None,
        )

        # Delete envelope and reconcile to mark abandoned
        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        db_sessions.response.delete(envelope)
        db_sessions.response.commit()

        result = reconcile_orphaned_sessions(
            db_sessions.core,
            db_sessions.response,
            encryption_settings=_FAKE_ENC_SETTINGS,
            locator_service=loc_svc,
        )
        assert result.abandoned == 1

        with pytest.raises(SessionInvalidError, match="abandoned"):
            load_current_session(
                db_sessions.core,
                db_sessions.response,
                browser_token,
                encryption_settings=_FAKE_ENC_SETTINGS,
                locator_service=loc_svc,
            )


class TestKmsFailureStillRollsBack:
    def test_kms_failure_rolls_back_not_abandoned(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "recon-kms-fail")

        dek_svc = MagicMock()
        dek_svc.create_for_session.side_effect = KmsError("KMS encrypt failed")

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=dek_svc,
            encryption_settings=_FAKE_ENC_SETTINGS,
        )
        with pytest.raises(SessionStartError):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("recon-kms-fail"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(
                SubmissionSession.survey_id == survey_id
            )
        )
        assert session is None, "core session must be rolled back, not abandoned"
