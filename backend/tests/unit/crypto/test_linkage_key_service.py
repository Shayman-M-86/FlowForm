"""Unit tests for linkage key access functions."""

from __future__ import annotations

import base64
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.cache import LockedTTLCache
from app.crypto._internal.errors import LinkageKeyError
from app.crypto._internal.linkage_keys import get_current_linkage_key, get_linkage_key_by_version
from app.crypto._internal.models import SecretValue
from app.crypto.models import LinkageKey

_GOOD_SECRET_BYTES = b"\xaa" * 32
_GOOD_SECRET_B64 = base64.b64encode(_GOOD_SECRET_BYTES).decode()
_VID_1 = "00000000-0000-0000-0000-000000000001"
_VID_2 = "00000000-0000-0000-0000-000000000002"

_LINKAGE_KEYS_MODULE = "app.crypto._internal.linkage_keys"


def _secret_value(version: int, aws_vid: str = _VID_1) -> SecretValue:
    import json

    raw = json.dumps({"version": version, "secret_b64": _GOOD_SECRET_B64})
    return SecretValue(secret_string=raw, version_id=aws_vid)


def _mock_cache():
    cache = MagicMock()
    cache.current_linkage_key = LockedTTLCache(name="test_current", maxsize=4, ttl_seconds=60)
    cache.linkage_keys_by_version = LockedTTLCache(name="test_versions", maxsize=4, ttl_seconds=60)
    return cache


def _db():
    return MagicMock()


class TestGetCurrentLinkageKey:
    def test_returns_key_from_aws(self) -> None:
        mock_cache = _mock_cache()
        with (
            patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache,
            patch(
                f"{_LINKAGE_KEYS_MODULE}.fetch_linkage_secret_from_aws",
                return_value=_secret_value(1),
            ),
            patch(f"{_LINKAGE_KEYS_MODULE}.linkage_key_repo") as repo,
        ):
            get_cache.return_value.crypto = mock_cache
            repo.version_exists.return_value = True
            key = get_current_linkage_key(_db())

        assert key.version == 1
        assert key.secret == _GOOD_SECRET_BYTES

    def test_caches_on_hit(self) -> None:
        mock_cache = _mock_cache()
        cached_key = LinkageKey(version=2, secret=_GOOD_SECRET_BYTES, aws_version_id=_VID_2)
        mock_cache.current_linkage_key.put("current", cached_key)

        with patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache:
            get_cache.return_value.crypto = mock_cache
            key = get_current_linkage_key(_db())

        assert key == cached_key

    def test_persists_new_version_row(self) -> None:
        mock_cache = _mock_cache()
        with (
            patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache,
            patch(
                f"{_LINKAGE_KEYS_MODULE}.fetch_linkage_secret_from_aws",
                return_value=_secret_value(3),
            ),
            patch(f"{_LINKAGE_KEYS_MODULE}.linkage_key_repo") as repo,
            patch(f"{_LINKAGE_KEYS_MODULE}.commit_with_err_handle"),
            patch(f"{_LINKAGE_KEYS_MODULE}.current_settings") as settings,
        ):
            get_cache.return_value.crypto = mock_cache
            repo.version_exists.return_value = False
            settings.return_value.flowform.encryption.linkage_secret_arn = "arn:test"
            get_current_linkage_key(_db())

        repo.insert_version.assert_called_once()


class TestGetLinkageKeyByVersion:
    def test_returns_from_cache(self) -> None:
        mock_cache = _mock_cache()
        cached_key = LinkageKey(version=1, secret=_GOOD_SECRET_BYTES, aws_version_id=_VID_1)
        mock_cache.linkage_keys_by_version.put(1, cached_key)

        with patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache:
            get_cache.return_value.crypto = mock_cache
            key = get_linkage_key_by_version(1, _db())

        assert key == cached_key

    def test_fetches_from_aws_on_cache_miss(self) -> None:
        mock_cache = _mock_cache()
        with (
            patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache,
            patch(f"{_LINKAGE_KEYS_MODULE}.linkage_key_repo") as repo,
            patch(
                f"{_LINKAGE_KEYS_MODULE}.fetch_linkage_secret_from_aws",
                return_value=_secret_value(2, aws_vid=_VID_2),
            ),
        ):
            get_cache.return_value.crypto = mock_cache
            repo.get_aws_version_id.return_value = uuid.UUID(_VID_2.ljust(32, "0").replace("-", "")[:32])
            key = get_linkage_key_by_version(2, _db())

        assert key.version == 2

    def test_missing_version_raises(self) -> None:
        mock_cache = _mock_cache()
        with (
            patch(f"{_LINKAGE_KEYS_MODULE}.get_app_cache") as get_cache,
            patch(f"{_LINKAGE_KEYS_MODULE}.linkage_key_repo") as repo,
        ):
            get_cache.return_value.crypto = mock_cache
            repo.get_aws_version_id.return_value = None

            with pytest.raises(LinkageKeyError):
                get_linkage_key_by_version(99, _db())
