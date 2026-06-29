"""Contract tests for opaque locator derivation."""

from __future__ import annotations

from uuid import UUID

from app.crypto._internal.locators import derive_answer_locator, derive_session_locator

SESSION_1 = UUID("00000000-0000-0000-0000-000000000001")
SESSION_2 = UUID("00000000-0000-0000-0000-000000000002")
SLOT_1 = UUID("10000000-0000-0000-0000-000000000001")
SLOT_2 = UUID("10000000-0000-0000-0000-000000000002")

SECRET_1 = b"a" * 32
SECRET_2 = b"b" * 32


def test_session_locator_is_deterministic_for_same_session_and_secret() -> None:
    """The same session ID and linkage secret should derive the same locator."""
    assert derive_session_locator(SESSION_1, SECRET_1) == derive_session_locator(SESSION_1, SECRET_1)


def test_session_locator_changes_for_different_sessions() -> None:
    """Different core sessions should not share locators under one secret."""
    assert derive_session_locator(SESSION_1, SECRET_1) != derive_session_locator(SESSION_2, SECRET_1)


def test_session_locator_changes_for_different_linkage_secret() -> None:
    """Changing linkage secret material should change locator output."""
    assert derive_session_locator(SESSION_1, SECRET_1) != derive_session_locator(SESSION_1, SECRET_2)


def test_session_locator_is_opaque_32_byte_value() -> None:
    """Session locators should be fixed-size opaque values, not raw UUID bytes."""
    locator = derive_session_locator(SESSION_1, SECRET_1)

    assert len(locator) == 32
    assert SESSION_1.bytes not in locator


def test_answer_locator_is_deterministic_for_same_slot_and_secret() -> None:
    """The same answer slot ID and linkage secret should derive the same locator."""
    assert derive_answer_locator(SLOT_1, SECRET_1) == derive_answer_locator(SLOT_1, SECRET_1)


def test_answer_locator_changes_for_different_slots() -> None:
    """Different answer slots should not share locators under one secret."""
    assert derive_answer_locator(SLOT_1, SECRET_1) != derive_answer_locator(SLOT_2, SECRET_1)


def test_answer_locator_is_opaque_32_byte_value() -> None:
    """Answer locators should be fixed-size opaque values, not raw UUID bytes."""
    locator = derive_answer_locator(SLOT_1, SECRET_1)

    assert len(locator) == 32
    assert SLOT_1.bytes not in locator
