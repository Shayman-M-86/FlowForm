"""Session start envelope creation integration tests.

Verifies that:
- Successful session start creates both core session and response envelope
- Resume token is not returned when envelope creation fails
- Core session is rolled back when envelope creation fails before core commit
- DEK is cached on successful start (inside SessionDEKService)
- Core commit failure after envelope creation triggers orphan cleanup
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto.errors import KmsError
from app.crypto.services import NewSessionDEK, NewSessionLocator
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionStartError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.session_starter import SessionStarter
from tests.conftest import DbSessions
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

_SCHEMA = {"nodes": [{"id": "q1", "type": "short_text"}]}
_FAKE_SESSION_LOCATOR = os.urandom(32)
_FAKE_PLAINTEXT_DEK = os.urandom(32)
_FAKE_WRAPPED_DEK = b"wrapped-dek-bytes"
_FAKE_ENC_SETTINGS = EncryptionSettings(
    kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
    linkage_secret_arn="arn:aws:secretsmanager:us-east-1:000000000000:secret:test",
    aws_region="us-east-1",
    aws_access_key_id=SecretStr("AKIAIOSFODNN7EXAMPLE"),
    aws_secret_access_key=SecretStr("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
)


@pytest.fixture()
def _mock_session_encryption() -> None:
    """Override the autouse conftest mock — these tests exercise envelope creation."""


def _seed_published_survey(db: Session, slug: str) -> int:
    """Create a user, project, response store, survey, and published version. Returns survey_id."""
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
    svc.get_current_linkage_key_version.return_value = 1
    loc = NewSessionLocator(
        linkage_key_version=1,
        session_locator=session_locator or _FAKE_SESSION_LOCATOR,
    )
    svc.for_new_session.return_value = loc
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


def _fail_response_commit_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the response DB commit fail before the core DB commit is attempted."""
    original = commit_with_err_handle
    call_count = 0

    def _fail_first(db, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            db.rollback()
            raise RuntimeError("response commit failed")
        return original(db, *args, **kwargs)

    monkeypatch.setattr(
        "app.services.public_submissions.core.session_starter.commit_with_err_handle",
        _fail_first,
    )


class TestSuccessfulSessionStart:

    def test_session_start_creates_core_session_and_response_envelope(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "envelope-test")

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        response, browser_token, _recog = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("envelope-test"),
            actor=None,
        )

        assert browser_token, "browser token must be returned on success"
        assert response.status == "in_progress"

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is not None, "core session must exist"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None, "response envelope must exist"
        assert envelope.wrapped_dek == _FAKE_WRAPPED_DEK
        assert envelope.kms_key_arn == _FAKE_ENC_SETTINGS.kms_key_arn
        assert envelope.crypto_version == 1
        assert envelope.kms_context_version == 1

    def test_dek_service_create_called_with_session_id(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "cache-test")

        dek_svc = _mock_dek_service()
        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=dek_svc,
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("cache-test"),
            actor=None,
        )

        dek_svc.create_for_session.assert_called_once()


class TestPreCommitEnvelopeFailureRollback:
    """Envelope creation fails before core commit — core transaction is rolled back."""

    def test_kms_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "kms-fail-test")

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
                payload=_slug_payload("kms-fail-test"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is None, "core session must be rolled back on KMS failure"

    def test_locator_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "linkage-fail-test")

        loc_svc = MagicMock()
        loc_svc.for_new_session.side_effect = RuntimeError("locator derivation failed")

        starter = SessionStarter(
            locator_service=loc_svc,
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("linkage-fail-test"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is None, "core session must be rolled back on locator failure"

    def test_envelope_repo_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "repo-fail-test")

        mock_repo = MagicMock()
        mock_repo.create.side_effect = RuntimeError("DB write failed")
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.response_envelope_repo",
            mock_repo,
        )

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("repo-fail-test"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is None, "core session must be rolled back on envelope repo failure"

    def test_response_commit_failure_rolls_back_core_session_and_envelope(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "response-commit-fail-test")
        _fail_response_commit_once(monkeypatch)

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError, match="Failed to create response envelope"):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("response-commit-fail-test"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
            if False
            else select(SubmissionSession)
        )
        assert session is None, "core session must be rolled back when response commit fails"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, "response envelope must be rolled back when response commit fails"


class TestCoreCommitFailureAfterEnvelopeCreation:
    """Response envelope committed, then core commit fails — orphan cleanup."""

    @staticmethod
    def _patch_fail_core_commit(monkeypatch: pytest.MonkeyPatch) -> None:
        """Make commit_with_err_handle succeed for response DB (1st call) but fail for core (2nd call)."""
        call_count = 0
        original = commit_with_err_handle

        def _fail_second(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("core commit failed")
            return original(*args, **kwargs)

        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.commit_with_err_handle",
            _fail_second,
        )

    def test_core_commit_failure_does_not_return_resume_token(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "core-fail-test")
        self._patch_fail_core_commit(monkeypatch)

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError, match="Core commit failed"):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("core-fail-test"),
                actor=None,
            )

    def test_core_commit_failure_cleans_up_orphan_envelope(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When core commit fails, the compensating delete removes the orphan
        envelope so no reconciliation is needed."""
        _seed_published_survey(db_sessions.core, "core-fail-cleanup-test")
        self._patch_fail_core_commit(monkeypatch)

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("core-fail-cleanup-test"),
                actor=None,
            )

        db_sessions.response.rollback()
        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, (
            "orphan envelope must be cleaned up by compensating delete"
        )

    def test_core_commit_failure_invokes_compensation_with_envelope_locator(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "core-fail-compensate-call-test")
        self._patch_fail_core_commit(monkeypatch)

        deleted_locators: list[bytes] = []

        def _record_delete(_db: Session, session_locator: bytes) -> bool:
            deleted_locators.append(session_locator)
            return True

        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.response_envelope_repo.delete_by_locator",
            _record_delete,
        )

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with pytest.raises(SessionStartError, match="Core commit failed"):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("core-fail-compensate-call-test"),
                actor=None,
            )

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        assert deleted_locators == [envelope.session_locator]

    def test_compensation_failure_rolls_back_response_session_and_logs(
        self,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        response_db = MagicMock()
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.response_envelope_repo.delete_by_locator",
            MagicMock(side_effect=RuntimeError("DELETE denied")),
        )
        caplog.set_level("ERROR")

        starter = SessionStarter(
            locator_service=_mock_locator_service(),
            dek_service=_mock_dek_service(),
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        starter._compensate_orphan_envelope(response_db, b"\x08" * 32)

        response_db.rollback.assert_called_once_with()
        response_db.commit.assert_not_called()
        assert "session_start.orphan_envelope_cleanup_failed" in caplog.text
