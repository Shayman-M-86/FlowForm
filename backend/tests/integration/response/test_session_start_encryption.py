"""Integration tests for session start encryption flows.

Verifies end-to-end that:
- Successful start creates core session + response envelope; resume cookie set
- Envelope creation failure rolls back the uncommitted core session; no resume cookie returned
- Resumed session: loader finds existing session, returns correct frozen survey version
- Response DB locators are opaque 32-byte HMAC digests, not UUIDs or plaintext
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto.kms import KmsError
from app.domain.errors import SessionNotFoundError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.session_loader import load_current_session
from app.services.public_submissions.core.session_starter import SessionStarter
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
_FAKE_LINKAGE_SECRET = b"\xaa" * 32
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


def _patch_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.public_submissions.core.session_starter.get_linkage_secret",
        lambda *a, **kw: _FAKE_LINKAGE_SECRET,
    )
    monkeypatch.setattr(
        "app.services.public_submissions.core.session_starter.wrap_dek",
        lambda plaintext_dek, *a, **kw: _FAKE_WRAPPED_DEK,
    )


def _patch_loader_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.public_submissions.core.session_loader.get_linkage_secret",
        lambda *a, **kw: _FAKE_LINKAGE_SECRET,
    )


class TestSuccessfulSessionStart:

    def test_creates_core_session_and_response_envelope(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "enc-start-ok")
        _patch_crypto(monkeypatch)

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        response, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("enc-start-ok"),
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
        assert envelope.session_locator is not None

    def test_session_locator_is_opaque_32_bytes(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-locator-check")
        _patch_crypto(monkeypatch)

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
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
        core_id_bytes = str(session.id).encode("utf-8")
        assert locator != core_id_bytes, (
            "session_locator must not be the raw core session UUID"
        )

    def test_resume_cookie_set_on_success(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-resume-cookie")
        _patch_crypto(monkeypatch)

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        _, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("enc-resume-cookie"),
            actor=None,
        )

        assert len(browser_token) > 0, "resume token must be non-empty"

    def test_wrap_dek_called_on_session_start(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-wrap-assert")
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.get_linkage_secret",
            lambda *a, **kw: _FAKE_LINKAGE_SECRET,
        )
        wrap_mock = MagicMock(return_value=_FAKE_WRAPPED_DEK)
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.wrap_dek",
            wrap_mock,
        )

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("enc-wrap-assert"),
            actor=None,
        )

        wrap_mock.assert_called_once()
        call_args = wrap_mock.call_args
        plaintext_dek_arg = call_args[0][0]
        assert isinstance(plaintext_dek_arg, bytes), "wrap_dek must receive a bytes DEK"
        assert len(plaintext_dek_arg) == 32, "DEK must be 32 bytes (AES-256)"


class TestEnvelopeCreationFailure:

    def test_kms_failure_rolls_back_core_session(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.domain.errors import SessionStartError

        survey_id = _seed_published_survey(db_sessions.core, "enc-kms-fail")
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.get_linkage_secret",
            lambda *a, **kw: _FAKE_LINKAGE_SECRET,
        )
        monkeypatch.setattr(
            "app.services.public_submissions.core.session_starter.wrap_dek",
            MagicMock(side_effect=KmsError("KMS encrypt failed")),
        )

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        with pytest.raises(SessionStartError):
            starter.start(
                db_sessions.core,
                db_sessions.response,
                payload=_slug_payload("enc-kms-fail"),
                actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id)
        )
        assert session is None, "core session must be rolled back on KMS failure"

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is None, "no response envelope should exist on KMS failure"


class TestResumedSession:

    def test_loader_finds_existing_session(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "enc-resume-load")
        _patch_crypto(monkeypatch)

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        _, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("enc-resume-load"),
            actor=None,
        )

        _patch_loader_crypto(monkeypatch)
        ctx = load_current_session(
            db_sessions.core,
            db_sessions.response,
            browser_token,
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        assert ctx.session is not None
        assert ctx.session.survey_id == survey_id
        assert ctx.survey_version is not None
        assert ctx.envelope is not None
        assert ctx.session_locator is not None
        assert len(ctx.session_locator) == 32

    def test_loader_returns_correct_frozen_survey_version(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_published_survey(db_sessions.core, "enc-resume-version")
        _patch_crypto(monkeypatch)

        starter = SessionStarter(encryption_settings=_FAKE_ENC_SETTINGS)
        _, browser_token, _ = starter.start(
            db_sessions.core,
            db_sessions.response,
            payload=_slug_payload("enc-resume-version"),
            actor=None,
        )

        _patch_loader_crypto(monkeypatch)
        ctx = load_current_session(
            db_sessions.core,
            db_sessions.response,
            browser_token,
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        assert ctx.survey_version.status == "published"
        assert ctx.survey_version.compiled_schema == _SCHEMA

    def test_loader_rejects_invalid_token(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_loader_crypto(monkeypatch)
        with pytest.raises(SessionNotFoundError):
            load_current_session(
                db_sessions.core,
                db_sessions.response,
                "bogus-token-that-does-not-exist",
                encryption_settings=_FAKE_ENC_SETTINGS,
            )
