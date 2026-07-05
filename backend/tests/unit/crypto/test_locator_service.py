"""Unit tests for locator derivation functions."""

from __future__ import annotations

import uuid

from app.crypto._internal.locators import derive_answer_locator, derive_session_locator
from app.crypto.locators import (
    derive_answer_locator as public_derive_answer_locator,
)
from app.crypto.locators import (
    derive_session_locator as public_derive_session_locator,
)
from app.crypto.models import LinkageKey

_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")


class TestDeriveSessionLocator:
    def test_deterministic(self) -> None:
        sid = uuid.uuid4()
        loc1 = derive_session_locator(sid, _LINKAGE_SECRET)
        loc2 = derive_session_locator(sid, _LINKAGE_SECRET)
        assert loc1 == loc2

    def test_different_sessions_differ(self) -> None:
        loc1 = derive_session_locator(uuid.uuid4(), _LINKAGE_SECRET)
        loc2 = derive_session_locator(uuid.uuid4(), _LINKAGE_SECRET)
        assert loc1 != loc2

    def test_different_secrets_differ(self) -> None:
        sid = uuid.uuid4()
        loc1 = derive_session_locator(sid, b"\xaa" * 32)
        loc2 = derive_session_locator(sid, b"\xbb" * 32)
        assert loc1 != loc2

    def test_length_is_32_bytes(self) -> None:
        loc = derive_session_locator(uuid.uuid4(), _LINKAGE_SECRET)
        assert len(loc) == 32

    def test_not_raw_uuid(self) -> None:
        sid = uuid.uuid4()
        loc = derive_session_locator(sid, _LINKAGE_SECRET)
        assert loc != sid.bytes


class TestDeriveAnswerLocator:
    def test_deterministic(self) -> None:
        slot_id = uuid.uuid4()
        loc1 = derive_answer_locator(slot_id, _LINKAGE_SECRET)
        loc2 = derive_answer_locator(slot_id, _LINKAGE_SECRET)
        assert loc1 == loc2

    def test_different_slots_differ(self) -> None:
        loc1 = derive_answer_locator(uuid.uuid4(), _LINKAGE_SECRET)
        loc2 = derive_answer_locator(uuid.uuid4(), _LINKAGE_SECRET)
        assert loc1 != loc2

    def test_length_is_32_bytes(self) -> None:
        loc = derive_answer_locator(uuid.uuid4(), _LINKAGE_SECRET)
        assert len(loc) == 32


class TestPublicDeriveSessionLocator:
    def test_returns_new_session_locator(self) -> None:
        sid = uuid.uuid4()
        result = public_derive_session_locator(sid, _FAKE_LINKAGE_KEY)
        assert result.linkage_key_version == 1
        assert len(result.session_locator) == 32

    def test_deterministic(self) -> None:
        sid = uuid.uuid4()
        a = public_derive_session_locator(sid, _FAKE_LINKAGE_KEY)
        b = public_derive_session_locator(sid, _FAKE_LINKAGE_KEY)
        assert a.session_locator == b.session_locator


class TestPublicDeriveAnswerLocator:
    def test_returns_32_bytes(self) -> None:
        slot_id = uuid.uuid4()
        result = public_derive_answer_locator(slot_id, _FAKE_LINKAGE_KEY)
        assert isinstance(result, bytes)
        assert len(result) == 32
