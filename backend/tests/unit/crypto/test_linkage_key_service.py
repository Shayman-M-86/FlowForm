"""Unit tests for LinkageKeyService."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from app.crypto.errors import (
    LinkageKeyError,
    LinkageKeyUnavailableError,
    LinkageSecretError,
)
from app.crypto.linkage_key_service import (
    LinkageKey,
    LinkageKeyService,
)


def _make_service(**overrides: object) -> LinkageKeyService:
    defaults: dict[str, object] = {
        "current_key_secret_arn": "arn:aws:secretsmanager:us-east-1:000:secret:current",
        "versioned_key_secret_arn_template": "arn:aws:secretsmanager:us-east-1:000:secret:linkage-v{version}",
        "region": "us-east-1",
        "access_key_id": SecretStr("fake-id"),
        "secret_access_key": SecretStr("fake-secret"),
    }
    defaults.update(overrides)
    return LinkageKeyService(**defaults)  # type: ignore[arg-type]


_GOOD_SECRET_BYTES = b"\xaa" * 32
_GOOD_SECRET_B64 = base64.b64encode(_GOOD_SECRET_BYTES).decode()


def _versioned_payload(version: int, secret_b64: str = _GOOD_SECRET_B64) -> str:
    return json.dumps({"version": version, "secret_b64": secret_b64})


def _current_pointer(version: int) -> str:
    return json.dumps({"current_version": version})


class TestGetLinkageKey:
    def test_returns_current_version_and_secret(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.side_effect = [_current_pointer(2), _versioned_payload(2)]
            key = svc.get_linkage_key()
        assert key == LinkageKey(version=2, secret=_GOOD_SECRET_BYTES)

    def test_uses_cache_on_second_call(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.side_effect = [_current_pointer(2), _versioned_payload(2)]
            svc.get_linkage_key()
            key = svc.get_linkage_key()
        assert mock.call_count == 2  # pointer + versioned, then both cached
        assert key.version == 2


class TestGetLinkageKeyByVersion:
    def test_returns_requested_version(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _versioned_payload(1)
            key = svc.get_linkage_key_by_version(1)
        assert key == LinkageKey(version=1, secret=_GOOD_SECRET_BYTES)

    def test_different_versions_cached_separately(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.side_effect = [_versioned_payload(1), _versioned_payload(2)]
            k1 = svc.get_linkage_key_by_version(1)
            k2 = svc.get_linkage_key_by_version(2)
        assert k1.version == 1
        assert k2.version == 2
        assert mock.call_count == 2

        # Third call for v1 should not fetch again
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            k1_again = svc.get_linkage_key_by_version(1)
        mock.assert_not_called()
        assert k1_again == k1


class TestCacheExpiry:
    def test_expired_entry_triggers_refetch(self) -> None:
        svc = _make_service(cache_ttl_seconds=1.0)
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _versioned_payload(1)
            svc.get_linkage_key_by_version(1)

        with patch("app.crypto.linkage_key_service.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock_fetch:
                mock_fetch.return_value = _versioned_payload(1)
                svc.get_linkage_key_by_version(1)
            mock_fetch.assert_called_once()


class TestValidationErrors:
    def test_invalid_json_raises(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value="not-json"):
            with pytest.raises(LinkageKeyError, match="not valid JSON"):
                svc.get_linkage_key_by_version(1)

    def test_version_mismatch_raises(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _versioned_payload(99)
            with pytest.raises(LinkageKeyError, match="Version mismatch"):
                svc.get_linkage_key_by_version(1)

    def test_missing_secret_b64_raises(self) -> None:
        svc = _make_service()
        payload = json.dumps({"version": 1})
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value=payload):
            with pytest.raises(LinkageKeyError, match="missing 'secret_b64'"):
                svc.get_linkage_key_by_version(1)

    def test_invalid_base64_raises(self) -> None:
        svc = _make_service()
        payload = json.dumps({"version": 1, "secret_b64": "!!not-base64!!"})
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value=payload):
            with pytest.raises(LinkageKeyError, match="Invalid base64"):
                svc.get_linkage_key_by_version(1)

    def test_secret_too_short_raises(self) -> None:
        svc = _make_service()
        short = base64.b64encode(b"\x01" * 16).decode()
        payload = json.dumps({"version": 1, "secret_b64": short})
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value=payload):
            with pytest.raises(LinkageKeyError, match="too short"):
                svc.get_linkage_key_by_version(1)

    def test_empty_decoded_secret_raises(self) -> None:
        svc = _make_service()
        # " " is non-empty string but decodes to whitespace padding → 0 bytes
        payload = json.dumps({"version": 1, "secret_b64": "IA=="})
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value=payload):
            with pytest.raises(LinkageKeyError, match="too short"):
                svc.get_linkage_key_by_version(1)

    def test_invalid_current_version_pointer_raises(self) -> None:
        svc = _make_service()
        with patch("app.crypto.linkage_key_service.get_linkage_secret", return_value='{"bad": true}'):
            with pytest.raises(LinkageKeyError, match="current_version"):
                svc.get_linkage_key()


class TestAwsFailureTranslation:
    def test_aws_failure_raises_unavailable(self) -> None:
        svc = _make_service()
        with patch(
            "app.crypto.linkage_key_service.get_linkage_secret",
            side_effect=LinkageSecretError("boom"),
        ), pytest.raises(LinkageKeyUnavailableError):
            svc.get_linkage_key_by_version(1)
