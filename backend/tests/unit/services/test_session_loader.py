"""Unit tests for session loader state rejection logic."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.cache import create_app_cache
from app.crypto.models import LinkageKey, PlaintextSessionKey, SessionLocator, SubmissionSessionContext
from app.domain.errors import (
    EnvelopeNotFoundError,
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.schema.orm.core.submission_session import SessionRef
from app.services.public_submissions.core.session_loader import load_current_session


def _fake_session(
    *,
    status: str = "in_progress",
    expired: bool = False,
    session_id: uuid.UUID | None = None,
    survey_version_id: int = 1,
) -> MagicMock:
    session = MagicMock()
    session.id = session_id or uuid.uuid4()
    session.project_id = 10
    session.survey_id = 20
    session.session_status = status
    session.survey_version_id = survey_version_id
    session.linkage_key_version = 1
    session.browser_session_token_hash = b"\x00" * 32
    if expired:
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
    else:
        session.expires_at = datetime.now(UTC) + timedelta(hours=1)
    session.to_crypto_ref.return_value = SessionRef(
        id=session.id,
        project_id=session.project_id,
        survey_id=session.survey_id,
        survey_version_id=session.survey_version_id,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )
    return session


def _linkage_key() -> LinkageKey:
    return LinkageKey(
        version=1,
        secret=b"\x03" * 32,
        aws_version_id="11111111-1111-1111-1111-111111111111",
    )


def _cached_context(
    *,
    token_hash: bytes = b"\x00" * 32,
    expired: bool = False,
) -> SubmissionSessionContext:
    expires_at = datetime.now(UTC) - timedelta(hours=1) if expired else datetime.now(UTC) + timedelta(hours=1)
    return SubmissionSessionContext(
        session_id=uuid.uuid4(),
        project_id=10,
        survey_id=20,
        survey_version_id=1,
        envelope_id=uuid.uuid4(),
        session_locator=SessionLocator(b"\x02" * 32),
        linkage_key=_linkage_key(),
        linkage_key_version=1,
        _session_dek=PlaintextSessionKey(b"\x04" * 32),
        crypto_version=1,
        expires_at=expires_at,
        browser_session_token_hash=token_hash,
    )


def _load(db: MagicMock, response_db: MagicMock, raw_token: str, **kwargs):
    return load_current_session(
        db,
        response_db,
        raw_token,
        cache=kwargs.pop("cache", create_app_cache()),
        clients=kwargs.pop("clients", MagicMock()),
        **kwargs,
    )


class TestSessionLoaderRejection:
    def test_cached_context_returned_before_core_session_lookup(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        token_hash = b"\x00" * 32
        cache = create_app_cache()
        cached = _cached_context(token_hash=token_hash)

        cache.sessions.write_context.put(token_hash, cached)
        try:
            with patch(
                "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
                return_value=token_hash,
            ), patch(
                "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            ) as get_by_token_hash:
                ctx = _load(db, response_db, "some-token", cache=cache)

            assert ctx.session_id == cached.session_id
            get_by_token_hash.assert_not_called()
            response_db.get.assert_not_called()
        finally:
            cache.sessions.write_context.evict(token_hash)

    def test_expired_cached_context_raises_before_core_session_lookup(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        token_hash = b"\x00" * 32
        cache = create_app_cache()
        cached = _cached_context(token_hash=token_hash, expired=True)

        cache.sessions.write_context.put(token_hash, cached)
        try:
            with patch(
                "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
                return_value=token_hash,
            ), patch(
                "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            ) as get_by_token_hash, pytest.raises(SessionExpiredError):
                _load(db, response_db, "some-token", cache=cache)

            get_by_token_hash.assert_not_called()
        finally:
            cache.sessions.write_context.evict(token_hash)

    def test_missing_session_raises(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=None,
        ), pytest.raises(SessionNotFoundError):
            _load(db, response_db, "some-token")

    def test_expired_session_raises(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session(expired=True)
        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), pytest.raises(SessionExpiredError):
            _load(db, response_db, "some-token")

    def test_abandoned_session_raises(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session(status="abandoned")
        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), pytest.raises(SessionInvalidError, match="abandoned"):
            _load(db, response_db, "some-token")

    def test_completed_session_raises_when_editing(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session(status="completed")
        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), pytest.raises(SessionInvalidError, match="completed"):
            _load(db, response_db, "some-token")

    def test_completed_session_allowed_when_flagged(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session(status="completed")
        expected = _cached_context(token_hash=b"\x00" * 32)

        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), patch(
            "app.services.public_submissions.core.session_loader.build_session_context",
            return_value=expected,
        ) as build_context:
            ctx = _load(db, response_db, "some-token", allow_completed=True)
            assert ctx is expected
            build_context.assert_called_once()

    def test_missing_envelope_raises(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session()

        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), patch(
            "app.services.public_submissions.core.session_loader.build_session_context",
            side_effect=EnvelopeNotFoundError(),
        ), pytest.raises(EnvelopeNotFoundError):
            _load(db, response_db, "some-token")
