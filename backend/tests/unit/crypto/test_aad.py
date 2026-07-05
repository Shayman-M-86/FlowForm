from __future__ import annotations

import uuid

from app.crypto._internal.aad import build_aad
from app.crypto.models import AnswerContext, AnswerLocator, PlaintextSessionKey


def _ctx(*, locator: bytes = b"a" * 32) -> AnswerContext:
    return AnswerContext(
        dek=PlaintextSessionKey(b"d" * 32),
        crypto_version=1,
        envelope_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        answer_locator=AnswerLocator(locator),
    )


def test_aad_is_stable_for_same_answer_context() -> None:
    assert build_aad(_ctx()) == build_aad(_ctx())


def test_different_locator_differs() -> None:
    assert build_aad(_ctx(locator=b"a" * 32)) != build_aad(_ctx(locator=b"b" * 32))
