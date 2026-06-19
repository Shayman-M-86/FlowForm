"""Unit tests for LinkageKeyService."""

from __future__ import annotations

import base64
import json
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from app.crypto.errors import (
    LinkageKeyError,
    LinkageKeyUnavailableError,
    LinkageSecretError,
)
from app.crypto.secrets import SecretValue
from app.crypto.services.linkage_key_service import (
    LinkageKey,
    LinkageKeyService,
)


def _make_service(**overrides: object) -> LinkageKeyService:
    defaults: dict[str, object] = {
        "linkage_secret_arn": "arn:aws:secretsmanager:us-east-1:000:secret:linkage",
        "region": "us-east-1",
        "access_key_id": SecretStr("fake-id"),
        "secret_access_key": SecretStr("fake-secret"),
    }
    defaults.update(overrides)
    return LinkageKeyService(**defaults)  # type: ignore[arg-type]


def _db() -> MagicMock:
    return MagicMock()


_GOOD_SECRET_BYTES = b"\xaa" * 32
_GOOD_SECRET_B64 = base64.b64encode(_GOOD_SECRET_BYTES).decode()
_VID_1 = "11111111-1111-1111-1111-111111111111"
_VID_2 = "22222222-2222-2222-2222-222222222222"
_DB_UUID_1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _secret_value(version: int, secret_b64: str = _GOOD_SECRET_B64, aws_vid: str = _VID_1) -> SecretValue:
    return SecretValue(
        secret_string=json.dumps({"version": version, "secret_b64": secret_b64}),
        version_id=aws_vid,
    )


def _bad_secret_value(raw: str, aws_vid: str = _VID_1) -> SecretValue:
    return SecretValue(secret_string=raw, version_id=aws_vid)


class TestGetLinkageKey:
    def test_returns_current_version_and_secret(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_secret_value(2, aws_vid=_VID_2)),
            patch("app.crypto.services.linkage_key_service.version_exists", return_value=True),
        ):
            key = svc.get_linkage_key(_db())
        assert key == LinkageKey(version=2, secret=_GOOD_SECRET_BYTES, aws_version_id=_VID_2)

    def test_inserts_db_row_for_new_version(self) -> None:
        svc = _make_service()
        db = _db()
        with (
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_secret_value(3, aws_vid=_VID_1)),
            patch("app.crypto.services.linkage_key_service.version_exists", return_value=False),
            patch("app.crypto.services.linkage_key_service.insert_version") as insert_mock,
        ):
            svc.get_linkage_key(db)
        insert_mock.assert_called_once_with(
            db,
            version=3,
            aws_secret_id="arn:aws:secretsmanager:us-east-1:000:secret:linkage",
            aws_secret_version_id=uuid.UUID(_VID_1),
            is_current=True,
        )

    def test_skips_insert_when_version_exists(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_secret_value(2)),
            patch("app.crypto.services.linkage_key_service.version_exists", return_value=True),
            patch("app.crypto.services.linkage_key_service.insert_version") as insert_mock,
        ):
            svc.get_linkage_key(_db())
        insert_mock.assert_not_called()

    def test_populates_cache_for_by_version(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_secret_value(2)),
            patch("app.crypto.services.linkage_key_service.version_exists", return_value=True),
        ):
            svc.get_linkage_key(_db())
        with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
            key = svc.get_linkage_key_by_version(2, _db())
        mock.assert_not_called()
        assert key.version == 2


class TestGetLinkageKeyByVersion:
    def test_returns_version_via_in_memory_map(self) -> None:
        svc = _make_service()
        with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _secret_value(2, aws_vid=_VID_2)
            svc.get_linkage_key_by_version(2, _db())
        assert mock.call_count == 1

        with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
            key = svc.get_linkage_key_by_version(2, _db())
        mock.assert_not_called()
        assert key.version == 2

    def test_falls_back_to_db_lookup(self) -> None:
        svc = _make_service()
        db = _db()
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1) as db_mock,
            patch("app.crypto.services.linkage_key_service.get_linkage_secret") as sm_mock,
        ):
            sm_mock.return_value = _secret_value(1, aws_vid=str(_DB_UUID_1))
            key = svc.get_linkage_key_by_version(1, db)

        db_mock.assert_called_once_with(db, 1)
        assert key.version == 1
        assert sm_mock.call_args.kwargs.get("version_id") == str(_DB_UUID_1)

    def test_raises_when_version_not_in_cache_or_db(self) -> None:
        svc = _make_service()
        with patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=None):
            with pytest.raises(LinkageKeyError, match="not found in cache or database"):
                svc.get_linkage_key_by_version(99, _db())

    def test_uses_in_memory_map_after_cache_expiry(self) -> None:
        svc = _make_service(cache_ttl_seconds=1.0)
        db = _db()
        with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _secret_value(1, aws_vid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            svc.get_linkage_key_by_version(1, db)

        with patch("app.crypto.services.linkage_key_service.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 9999
            with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
                mock.return_value = _secret_value(1, aws_vid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                svc.get_linkage_key_by_version(1, db)
            assert mock.call_args.kwargs.get("version_id") == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    def test_version_mismatch_from_aws_raises(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret") as sm_mock,
        ):
            sm_mock.return_value = _secret_value(99, aws_vid=str(_DB_UUID_1))
            with pytest.raises(LinkageKeyError, match="secret contains v99"):
                svc.get_linkage_key_by_version(1, _db())


class TestCacheExpiry:
    def test_expired_entry_triggers_refetch(self) -> None:
        svc = _make_service(cache_ttl_seconds=1.0)
        db = _db()
        with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock:
            mock.return_value = _secret_value(1)
            svc.get_linkage_key_by_version(1, db)

        with patch("app.crypto.services.linkage_key_service.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            with patch("app.crypto.services.linkage_key_service.get_linkage_secret") as mock_fetch:
                mock_fetch.return_value = _secret_value(1)
                svc.get_linkage_key_by_version(1, db)
            mock_fetch.assert_called_once()


class TestValidationErrors:
    def test_invalid_json_raises(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value("not-json")),
            pytest.raises(LinkageKeyError, match="not valid JSON"),
        ):
            svc.get_linkage_key_by_version(1, _db())

    def test_missing_version_raises(self) -> None:
        svc = _make_service()
        raw = json.dumps({"secret_b64": _GOOD_SECRET_B64})
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value(raw)),
            pytest.raises(LinkageKeyError, match="missing or invalid 'version'"),
        ):
            svc.get_linkage_key_by_version(1, _db())

    def test_missing_secret_b64_raises(self) -> None:
        svc = _make_service()
        raw = json.dumps({"version": 1})
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value(raw)),
            pytest.raises(LinkageKeyError, match="missing 'secret_b64'"),
        ):
            svc.get_linkage_key_by_version(1, _db())

    def test_invalid_base64_raises(self) -> None:
        svc = _make_service()
        raw = json.dumps({"version": 1, "secret_b64": "!!not-base64!!"})
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value(raw)),
            pytest.raises(LinkageKeyError, match="Invalid base64"),
        ):
            svc.get_linkage_key_by_version(1, _db())

    def test_secret_too_short_raises(self) -> None:
        svc = _make_service()
        short = base64.b64encode(b"\x01" * 16).decode()
        raw = json.dumps({"version": 1, "secret_b64": short})
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value(raw)),
            pytest.raises(LinkageKeyError, match="too short"),
        ):
            svc.get_linkage_key_by_version(1, _db())

    def test_empty_decoded_secret_raises(self) -> None:
        svc = _make_service()
        raw = json.dumps({"version": 1, "secret_b64": "IA=="})
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch("app.crypto.services.linkage_key_service.get_linkage_secret", return_value=_bad_secret_value(raw)),
            pytest.raises(LinkageKeyError, match="too short"),
        ):
            svc.get_linkage_key_by_version(1, _db())


class TestAwsFailureTranslation:
    def test_aws_failure_raises_unavailable(self) -> None:
        svc = _make_service()
        with (
            patch("app.crypto.services.linkage_key_service.get_aws_version_id", return_value=_DB_UUID_1),
            patch(
                "app.crypto.services.linkage_key_service.get_linkage_secret",
                side_effect=LinkageSecretError("boom"),
            ),
            pytest.raises(LinkageKeyUnavailableError),
        ):
            svc.get_linkage_key_by_version(1, _db())
