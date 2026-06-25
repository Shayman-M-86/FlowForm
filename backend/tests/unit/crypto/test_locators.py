"""Tests for locator derivation."""

import os
from uuid import UUID

from app.crypto._internal.locators import derive_answer_locator, derive_session_locator

SESS_1 = UUID("00000000-0000-0000-0000-000000000001")
SESS_2 = UUID("00000000-0000-0000-0000-000000000002")

Q1 = UUID("00000000-0000-0000-0000-000000000001")
Q2 = UUID("00000000-0000-0000-0000-000000000002")


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
        a = derive_answer_locator(SESS_1, Q1, secret)
        b = derive_answer_locator(SESS_1, Q1, secret)
        assert a == b

    def test_different_questions_differ(self) -> None:
        secret = os.urandom(32)
        a = derive_answer_locator(SESS_1, Q1, secret)
        b = derive_answer_locator(SESS_1, Q2, secret)
        assert a != b

    def test_session_locator_differs_from_answer_locator(self) -> None:
        secret = os.urandom(32)
        session_loc = derive_session_locator(SESS_1, secret)
        answer_loc = derive_answer_locator(SESS_1, Q1, secret)
        assert session_loc != answer_loc
