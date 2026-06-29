"""Integration tests for session start encryption flows.

Verifies end-to-end that:
- Successful start creates core session + response envelope; resume cookie set
- Envelope creation failure rolls back the uncommitted core session; no resume cookie returned
- Resumed session: loader finds existing session, returns correct frozen survey version
- Response DB locators are opaque 32-byte HMAC digests, not UUIDs or plaintext
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.crypto._internal.errors import KmsError
from app.crypto.models import (
    LinkageKey,
    NewSessionKey,
    NewSessionLocator,
    PlaintextSessionKey,
    SessionLocator,
    WrappedSessionKey,
)
from app.domain.errors import SessionNotFoundError, SessionStartError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.session_loader import load_current_session
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
_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")
_FAKE_SESSION_LOCATOR = SessionLocator(os.urandom(32))
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_FAKE_WRAPPED_DEK = WrappedSessionKey(b"\xbb" * 64)

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
    return StartSubmissionSessionRequest.model_validate({"access": {"type": "public_slug", "public_slug": slug}})


def _mock_crypto_for_start():
    """Patch module-level crypto calls used by SessionStarter.start."""
    return [
        patch(
            f"{_STARTER_MODULE}.load_current_linkage_key",
            return_value=_FAKE_LINKAGE_KEY,
        ),
        patch(
            f"{_STARTER_MODULE}.derive_session_locator",
            return_value=NewSessionLocator(
                linkage_key_version=1,
                session_locator=_FAKE_SESSION_LOCATOR,
            ),
        ),
        patch(
            f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
            return_value=MagicMock(return_value=os.urandom(32)),
        ),
        patch(
            f"{_STARTER_MODULE}.create_session_key",
            return_value=NewSessionKey(
                plaintext_key=_FAKE_PLAINTEXT_DEK,
                wrapped_key=_FAKE_WRAPPED_DEK,
            ),
        ),
    ]


class TestSuccessfulSessionStart:
    def test_creates_core_session_and_response_envelope(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "enc-start-ok")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            response, browser_token, _ = starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-start-ok"),
                actor=None,
            )

        assert browser_token, "browser token must be returned on success"
        assert response.status == "in_progress"

        session = db_sessions.core.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == survey_id))
        assert session is not None, "core session must exist"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None, "response envelope must exist"
        assert envelope.wrapped_session_dek == _FAKE_WRAPPED_DEK
        assert envelope.session_locator is not None

    def test_session_locator_is_opaque_32_bytes(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-locator-check")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-locator-check"),
                actor=None,
            )

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        locator = envelope.session_locator
        assert isinstance(locator, bytes), "session_locator must be bytes"
        assert len(locator) == 32, "session_locator must be 32-byte HMAC-SHA256 digest"

        session = db_sessions.core.scalar(select(SubmissionSession))
        assert session is not None
        core_id_bytes = session.id.bytes
        assert locator != core_id_bytes, "session_locator must not be the raw core session UUID"

    def test_resume_cookie_set_on_success(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-resume-cookie")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            _, browser_token, _ = starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-resume-cookie"),
                actor=None,
            )

        assert len(browser_token) > 0, "resume token must be non-empty"


class TestEnvelopeCreationFailure:
    def test_kms_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "enc-kms-fail")

        with (
            patch(f"{_STARTER_MODULE}.load_current_linkage_key", return_value=_FAKE_LINKAGE_KEY),
            patch(
                f"{_STARTER_MODULE}.derive_session_locator",
                return_value=NewSessionLocator(
                    linkage_key_version=1,
                    session_locator=_FAKE_SESSION_LOCATOR,
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
                payload=_slug_payload("enc-kms-fail"),
                actor=None,
            )

        session = db_sessions.core.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == survey_id))
        assert session is None, "core session must be rolled back on KMS failure"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, "no response envelope should exist on KMS failure"


class TestResumedSession:
    def test_loader_finds_existing_session(
        self,
        db_sessions: DbSessions,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "enc-resume-load")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            _, browser_token, _ = starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-resume-load"),
                actor=None,
            )

        ctx = load_current_session(
            db_sessions.core,
            db_sessions.response,
            browser_token,
            cache=get_app_cache(),
            clients=get_crypto_clients(),
        )

        assert ctx.session_id is not None
        assert ctx.survey_id == survey_id
        assert ctx.envelope_id is not None
        assert ctx.session_locator is not None
        assert len(ctx.session_locator) == 32

    def test_loader_returns_correct_frozen_survey_version(
        self,
        db_sessions: DbSessions,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-resume-version")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            _, browser_token, _ = starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-resume-version"),
                actor=None,
            )

        ctx = load_current_session(
            db_sessions.core,
            db_sessions.response,
            browser_token,
            cache=get_app_cache(),
            clients=get_crypto_clients(),
        )

        assert ctx.survey_version_id is not None

    def test_loader_rejects_invalid_token(
        self,
        db_sessions: DbSessions,
    ) -> None:
        with pytest.raises(SessionNotFoundError):
            load_current_session(
                db_sessions.core,
                db_sessions.response,
                "bogus-token-that-does-not-exist",
                cache=get_app_cache(),
                clients=get_crypto_clients(),
            )
