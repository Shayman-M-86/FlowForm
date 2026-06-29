"""Tests for locator derivation."""

import os
from uuid import UUID

from app.crypto._internal.locators import derive_answer_locator, derive_session_locator

SESS_1 = UUID("00000000-0000-0000-0000-000000000001")
SESS_2 = UUID("00000000-0000-0000-0000-000000000002")

SLOT_1 = UUID("10000000-0000-0000-0000-000000000001")
SLOT_2 = UUID("10000000-0000-0000-0000-000000000002")


class TestDeriveSessionLocator:
    def test_deterministic(self) -> None:
        secret = os.urandom(32)
        a = derive_session_locator(SESS_1, secret)
        b = derive_session_locator(SESS_1, secret)
        assert a == b

    def test_different_sessions_differ(self) -> None:
        secret = os.urandom(32)
        a = derive_session_locator(SESS_1, secret)
        b = derive_session_locator(SESS_2, secret)
        assert a != b

    def test_different_secrets_differ(self) -> None:
        a = derive_session_locator(SESS_1, os.urandom(32))
        b = derive_session_locator(SESS_1, os.urandom(32))
        assert a != b

    def test_output_is_32_bytes(self) -> None:
        result = derive_session_locator(SESS_1, os.urandom(32))
        assert len(result) == 32


class TestDeriveAnswerLocator:
    def test_deterministic(self) -> None:
        secret = os.urandom(32)
        a = derive_answer_locator(SLOT_1, secret)
        b = derive_answer_locator(SLOT_1, secret)
        assert a == b

    def test_different_slots_differ(self) -> None:
        secret = os.urandom(32)
        a = derive_answer_locator(SLOT_1, secret)
        b = derive_answer_locator(SLOT_2, secret)
        assert a != b
