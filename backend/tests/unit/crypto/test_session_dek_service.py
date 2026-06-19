"""Unit tests for SessionDEKService."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from app.crypto.errors import KmsError, SessionDEKUnavailableError
from app.crypto.session_dek_service import SessionDEKService


def _make_service() -> SessionDEKService:
    return SessionDEKService(
        region="us-east-1",
        access_key_id=SecretStr("fake-id"),
        secret_access_key=SecretStr("fake-secret"),
    )


_S1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_S2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
_WRAPPED = b"\x00" * 64
_PLAINTEXT = b"\xaa" * 32
_ARN = "arn:aws:kms:us-east-1:000:key/test"
_ARN_2 = "arn:aws:kms:us-east-1:000:key/test-2"
_EXPIRES = datetime.now(UTC) + timedelta(hours=1)


class TestGetForSession:
    def test_returns_plaintext_dek(self) -> None:
        svc = _make_service()
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT):
            dek = svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
        assert dek == _PLAINTEXT

    def test_caches_on_second_call(self) -> None:
        svc = _make_service()
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            dek = svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
        assert mock.call_count == 1
        assert dek == _PLAINTEXT

    def test_different_sessions_cached_separately(self) -> None:
        svc = _make_service()
        dek_a = b"\xaa" * 32
        dek_b = b"\xbb" * 32
        with patch("app.crypto.session_dek_service.unwrap_dek", side_effect=[dek_a, dek_b]) as mock:
            a = svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            b = svc.get_for_session(_S2, _WRAPPED, _ARN, _EXPIRES)
        assert mock.call_count == 2
        assert a == dek_a
        assert b == dek_b

    def test_different_kms_arns_cached_separately(self) -> None:
        svc = _make_service()
        dek_a = b"\xaa" * 32
        dek_b = b"\xbb" * 32
        with patch("app.crypto.session_dek_service.unwrap_dek", side_effect=[dek_a, dek_b]) as mock:
            a = svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            b = svc.get_for_session(_S1, _WRAPPED, _ARN_2, _EXPIRES)
        assert mock.call_count == 2
        assert a != b

    def test_expired_cache_triggers_refetch(self) -> None:
        svc = _make_service()
        short_expiry = datetime.now(UTC) + timedelta(seconds=1)
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT):
            svc.get_for_session(_S1, _WRAPPED, _ARN, short_expiry)

        with patch("app.crypto.session_dek_service.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
                svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            mock.assert_called_once()

    def test_passes_encryption_context(self) -> None:
        svc = _make_service()
        ctx = {"session_locator": "abc", "kms_context_version": "1"}
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES, encryption_context=ctx)
        assert mock.call_args[0][2] == ctx

    def test_kms_failure_raises_app_error(self) -> None:
        svc = _make_service()
        with patch(
            "app.crypto.session_dek_service.unwrap_dek",
            side_effect=KmsError("boom"),
        ), pytest.raises(SessionDEKUnavailableError):
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)

    def test_already_expired_session_not_cached(self) -> None:
        svc = _make_service()
        past = datetime.now(UTC) - timedelta(seconds=10)
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
            svc.get_for_session(_S1, _WRAPPED, _ARN, past)
            svc.get_for_session(_S1, _WRAPPED, _ARN, past)
        assert mock.call_count == 2


class TestClearForSession:
    def test_clears_all_arns_for_session(self) -> None:
        svc = _make_service()
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            svc.get_for_session(_S1, _WRAPPED, _ARN_2, _EXPIRES)
            svc.clear_for_session(_S1)
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            svc.get_for_session(_S1, _WRAPPED, _ARN_2, _EXPIRES)
        assert mock.call_count == 4

    def test_clear_missing_is_noop(self) -> None:
        svc = _make_service()
        svc.clear_for_session(_S1)


class TestClearExpired:
    def test_removes_expired_entries(self) -> None:
        svc = _make_service()
        short_expiry = datetime.now(UTC) + timedelta(seconds=1)
        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT):
            svc.get_for_session(_S1, _WRAPPED, _ARN, short_expiry)
            svc.get_for_session(_S2, _WRAPPED, _ARN, _EXPIRES)

        with patch("app.crypto.session_dek_service.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            svc.clear_expired()

        with patch("app.crypto.session_dek_service.unwrap_dek", return_value=_PLAINTEXT) as mock:
            svc.get_for_session(_S1, _WRAPPED, _ARN, _EXPIRES)
            svc.get_for_session(_S2, _WRAPPED, _ARN, _EXPIRES)
        assert mock.call_count == 1  # s1 refetched, s2 still cached
