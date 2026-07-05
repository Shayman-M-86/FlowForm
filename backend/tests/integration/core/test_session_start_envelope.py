"""Session start envelope creation integration tests.

Verifies that:
- Successful session start creates both core session and response envelope
- Core session is rolled back when envelope creation fails before core commit
- Core commit failure after envelope creation triggers orphan cleanup
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto._internal.errors import KmsError
from app.crypto.models import (
    LinkageKey,
    NewSessionKey,
    NewSessionLocator,
    PlaintextSessionKey,
    SessionLocator,
    WrappedSessionKey,
)
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import SessionStartError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from tests.conftest import DbSessions
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

_SCHEMA = {"nodes": [{"id": "q1", "type": "short_text"}]}
_FAKE_SESSION_LOCATOR = SessionLocator(os.urandom(32))
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_FAKE_WRAPPED_DEK = WrappedSessionKey(b"\xbb" * 64)
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=b"\xcc" * 32, aws_version_id="test-version")

_STARTER_MODULE = "app.services.public_submissions.core.actions.session_starter"


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


def _mock_crypto_for_start():
    return [
        patch(f"{_STARTER_MODULE}.load_current_linkage_key", return_value=_FAKE_LINKAGE_KEY),
        patch(
            f"{_STARTER_MODULE}.derive_session_locator",
            return_value=NewSessionLocator(linkage_key_version=1, session_locator=_FAKE_SESSION_LOCATOR),
        ),
        patch(
            f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
            return_value=MagicMock(return_value=os.urandom(32)),
        ),
        patch(
            f"{_STARTER_MODULE}.create_session_key",
            return_value=NewSessionKey(plaintext_key=_FAKE_PLAINTEXT_DEK, wrapped_key=_FAKE_WRAPPED_DEK),
        ),
    ]


def _fail_response_commit_once(monkeypatch: pytest.MonkeyPatch) -> None:
    original = commit_with_err_handle
    call_count = 0

    def _fail_first(db, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            db.rollback()
            raise RuntimeError("response commit failed")
        return original(db, *args, **kwargs)

    monkeypatch.setattr(f"{_STARTER_MODULE}.commit_with_err_handle", _fail_first)


class TestSuccessfulSessionStart:
    def test_session_start_creates_core_session_and_response_envelope(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "envelope-test")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            response, browser_token, _ = starter.start(
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
        assert envelope.wrapped_session_dek == _FAKE_WRAPPED_DEK
        assert envelope.crypto_version == 1


class TestPreCommitEnvelopeFailureRollback:
    def test_kms_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "kms-fail-test")

        with (
            patch(f"{_STARTER_MODULE}.load_current_linkage_key", return_value=_FAKE_LINKAGE_KEY),
            patch(
                f"{_STARTER_MODULE}.derive_session_locator",
                return_value=NewSessionLocator(
                    linkage_key_version=1, session_locator=_FAKE_SESSION_LOCATOR,
                ),
            ),
            patch(
                f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
                return_value=MagicMock(return_value=os.urandom(32)),
            ),
            patch(f"{_STARTER_MODULE}.create_session_key", side_effect=KmsError("KMS encrypt failed")),
            pytest.raises(SessionStartError),
        ):
            starter = SessionStarter()
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

    def test_envelope_repo_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "repo-fail-test")

        mock_repo = MagicMock()
        mock_repo.create.side_effect = RuntimeError("DB write failed")
        monkeypatch.setattr(f"{_STARTER_MODULE}.response_envelope_repo", mock_repo)

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3], pytest.raises(SessionStartError):
            starter = SessionStarter()
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
        survey_id = _seed_published_survey(db_sessions.core, "response-commit-fail-test")
        _fail_response_commit_once(monkeypatch)

        patches = _mock_crypto_for_start()
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            pytest.raises(SessionStartError, match="Failed to create response envelope"),
        ):
            starter = SessionStarter()
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("response-commit-fail-test"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is None, "core session must be rolled back when response commit fails"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, "response envelope must be rolled back when response commit fails"


class TestCoreCommitFailureAfterEnvelopeCreation:
    @staticmethod
    def _patch_fail_core_commit(monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0
        original = commit_with_err_handle

        def _fail_second(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("core commit failed")
            return original(*args, **kwargs)

        monkeypatch.setattr(f"{_STARTER_MODULE}.commit_with_err_handle", _fail_second)

    def test_core_commit_failure_does_not_return_resume_token(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "core-fail-test")
        self._patch_fail_core_commit(monkeypatch)

        patches = _mock_crypto_for_start()
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            pytest.raises(SessionStartError, match="Core commit failed"),
        ):
            starter = SessionStarter()
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
        _seed_published_survey(db_sessions.core, "core-fail-cleanup-test")
        self._patch_fail_core_commit(monkeypatch)

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3], pytest.raises(SessionStartError):
            starter = SessionStarter()
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("core-fail-cleanup-test"),
                actor=None,
            )

        db_sessions.response.rollback()
        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, "orphan envelope must be cleaned up by compensating delete"
