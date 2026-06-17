"""Unit tests for session loader state rejection logic."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.domain.errors import (
    EnvelopeNotFoundError,
    SessionExpiredError,
    SessionInvalidError,
    SessionNotFoundError,
)
from app.services.public_submissions.core.session_loader import load_current_session


def _fake_encryption_settings() -> MagicMock:
    enc = MagicMock()
    enc.linkage_secret_arn = "arn:aws:secretsmanager:us-east-1:000:secret:test"
    enc.kms_key_arn = "arn:aws:kms:us-east-1:000:key/test"
    enc.aws_region = "us-east-1"
    enc.aws_access_key_id = MagicMock()
    enc.aws_secret_access_key = MagicMock()
    return enc


def _fake_session(
    *,
    status: str = "in_progress",
    expired: bool = False,
    session_id: uuid.UUID | None = None,
    survey_version_id: int = 1,
) -> MagicMock:
    session = MagicMock()
    session.id = session_id or uuid.uuid4()
    session.session_status = status
    session.survey_version_id = survey_version_id
    session.linkage_key_version = 1
    if expired:
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
    else:
        session.expires_at = datetime.now(UTC) + timedelta(hours=1)
    return session


class TestSessionLoaderRejection:
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
            load_current_session(
                db, response_db, "some-token",
                encryption_settings=_fake_encryption_settings(),
            )

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
            load_current_session(
                db, response_db, "some-token",
                encryption_settings=_fake_encryption_settings(),
            )

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
            load_current_session(
                db, response_db, "some-token",
                encryption_settings=_fake_encryption_settings(),
            )

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
            load_current_session(
                db, response_db, "some-token",
                encryption_settings=_fake_encryption_settings(),
            )

    def test_completed_session_allowed_when_flagged(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session(status="completed")
        version = MagicMock()
        version.id = 1
        envelope = MagicMock()

        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), patch(
            "app.services.public_submissions.core.session_loader.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.derive_session_locator",
            return_value=b"\x02" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.response_envelope_repo.get_by_locator",
            return_value=envelope,
        ):
            db.scalar.return_value = version
            ctx = load_current_session(
                db, response_db, "some-token",
                allow_completed=True,
                encryption_settings=_fake_encryption_settings(),
            )
            assert ctx.session is session
            assert ctx.envelope is envelope

    def test_missing_envelope_raises(self) -> None:
        db = MagicMock()
        response_db = MagicMock()
        session = _fake_session()
        version = MagicMock()
        version.id = 1

        with patch(
            "app.services.public_submissions.core.session_loader.ssr.hash_browser_session_token",
            return_value=b"\x00" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.ssr.get_by_token_hash",
            return_value=session,
        ), patch(
            "app.services.public_submissions.core.session_loader.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.derive_session_locator",
            return_value=b"\x02" * 32,
        ), patch(
            "app.services.public_submissions.core.session_loader.response_envelope_repo.get_by_locator",
            return_value=None,
        ):
            db.scalar.return_value = version
            with pytest.raises(EnvelopeNotFoundError):
                load_current_session(
                    db, response_db, "some-token",
                    encryption_settings=_fake_encryption_settings(),
                )
