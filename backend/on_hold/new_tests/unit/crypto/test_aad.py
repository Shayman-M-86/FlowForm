"""Contract tests for answer encryption AAD construction."""

from __future__ import annotations

from uuid import UUID

from app.crypto._internal.aad import build_aad
from app.crypto.models import AnswerContext, AnswerLocator, PlaintextSessionKey

ENVELOPE_ID = UUID("11111111-1111-1111-1111-111111111111")


def _context(
    *,
    crypto_version: int = 1,
    envelope_id: UUID = ENVELOPE_ID,
    locator: bytes = b"a" * 32,
) -> AnswerContext:
    return AnswerContext(
        dek=PlaintextSessionKey(b"d" * 32),
        crypto_version=crypto_version,
        envelope_id=envelope_id,
        answer_locator=AnswerLocator(locator),
    )


def test_build_aad_is_stable_for_same_answer_context() -> None:
    """The same answer context should produce byte-for-byte identical AAD."""
    assert build_aad(_context()) == build_aad(_context())


def test_build_aad_changes_when_crypto_version_changes() -> None:
    """Crypto version is part of the authenticated context."""
    assert build_aad(_context(crypto_version=1)) != build_aad(_context(crypto_version=2))


def test_build_aad_changes_when_envelope_changes() -> None:
    """Envelope ID is part of the authenticated context."""
    assert build_aad(_context()) != build_aad(_context(envelope_id=UUID("22222222-2222-2222-2222-222222222222")))


def test_build_aad_changes_when_locator_changes() -> None:
    """Answer locator is part of the authenticated context."""
    assert build_aad(_context(locator=b"a" * 32)) != build_aad(_context(locator=b"b" * 32))
