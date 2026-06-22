"""Unit tests for LocatorService."""

from __future__ import annotations

import os
from typing import cast
from unittest.mock import MagicMock

from app.crypto.services.linkage_key_service import LinkageKey, LinkageKeyService
from app.crypto.services.locator_service import LocatorService, NewSessionLocator


def _db() -> MagicMock:
    return MagicMock()


def _make_service(
    current_version: int = 2,
    secrets: dict[int, bytes] | None = None,
) -> LocatorService:
    if secrets is None:
        secrets = {
            1: os.urandom(32),
            2: os.urandom(32),
        }
    keys = MagicMock(spec=LinkageKeyService)
    keys.get_linkage_key.side_effect = lambda db: LinkageKey(
        version=current_version, secret=secrets[current_version], aws_version_id="vid-test"
    )
    keys.get_linkage_key_by_version.side_effect = lambda v, db: LinkageKey(
        version=v, secret=secrets[v], aws_version_id=f"vid-{v}"
    )
    return LocatorService(keys)


class TestForNewSession:
    def test_returns_version_and_locator(self) -> None:
        svc = _make_service()
        result = svc.for_new_session("sess-1", _db())
        assert isinstance(result, NewSessionLocator)
        assert result.linkage_key_version == 2
        assert isinstance(result.session_locator, bytes)
        assert len(result.session_locator) == 32

    def test_deterministic(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        a = svc.for_new_session("sess-1", db)
        b = svc.for_new_session("sess-1", db)
        assert a == b

    def test_different_sessions_differ(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        a = svc.for_new_session("sess-1", db)
        b = svc.for_new_session("sess-2", db)
        assert a.session_locator != b.session_locator


class TestForExistingSession:
    def test_returns_same_locator_as_new(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        new = svc.for_new_session("sess-1", db)
        existing = svc.for_existing_session("sess-1", 2, db)
        assert new.session_locator == existing

    def test_uses_stored_version(self) -> None:
        secrets = {1: os.urandom(32), 2: os.urandom(32)}
        svc = _make_service(current_version=2, secrets=secrets)
        db = _db()
        loc_v1 = svc.for_existing_session("sess-1", 1, db)
        loc_v2 = svc.for_existing_session("sess-1", 2, db)
        assert loc_v1 != loc_v2


class TestAnswerLocator:
    def test_returns_32_bytes(self) -> None:
        svc = _make_service()
        loc = svc.answer_locator("sess-1", "q-1", 2, _db())
        assert isinstance(loc, bytes)
        assert len(loc) == 32

    def test_deterministic(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        a = svc.answer_locator("sess-1", "q-1", 2, db)
        b = svc.answer_locator("sess-1", "q-1", 2, db)
        assert a == b

    def test_different_questions_differ(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        a = svc.answer_locator("sess-1", "q-1", 2, db)
        b = svc.answer_locator("sess-1", "q-2", 2, db)
        assert a != b


class TestAnswerLocators:
    def test_returns_map(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        result = svc.answer_locators("sess-1", ["q-1", "q-2", "q-3"], 2, _db())
        assert set(result.keys()) == {"q-1", "q-2", "q-3"}
        assert all(len(v) == 32 for v in result.values())

    def test_matches_single_answer_locator(self) -> None:
        secret = os.urandom(32)
        svc = _make_service(secrets={2: secret})
        db = _db()
        batch = svc.answer_locators("sess-1", ["q-1"], 2, db)
        single = svc.answer_locator("sess-1", "q-1", 2, db)
        assert batch["q-1"] == single

    def test_fetches_key_once(self) -> None:
        svc = _make_service()
        db = _db()
        svc.answer_locators("sess-1", ["q-1", "q-2", "q-3"], 2, db)
        get_linkage_key_by_version = cast(MagicMock, svc._keys.get_linkage_key_by_version)
        get_linkage_key_by_version.assert_called_once_with(2, db)
