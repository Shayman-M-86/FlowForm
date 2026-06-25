"""Tests for AAD construction."""

import os
import uuid

from app.crypto._internal.aad import build_aad
from app.crypto.models import AnswerLocator, PlaintextSessionKey, RevisionContext

_UUID_A = uuid.UUID("00000000-0000-0000-0000-000000000064")
_UUID_B = uuid.UUID("00000000-0000-0000-0000-000000000065")
_UUID_C = uuid.UUID("00000000-0000-0000-0000-0000000000c8")
_UUID_D = uuid.UUID("00000000-0000-0000-0000-00000000012c")
_UUID_E = uuid.UUID("00000000-0000-0000-0000-00000000012d")
_DEK = PlaintextSessionKey(os.urandom(32))


def _ctx(
    envelope_id=_UUID_A,
    answer_id=_UUID_C,
    locator=b"\x01" * 32,
    revision_id=_UUID_D,
    revision_number=1,
) -> RevisionContext:
    return RevisionContext(
        dek=_DEK,
        crypto_version=1,
        envelope_id=envelope_id,
        answer_id=answer_id,
        answer_locator=AnswerLocator(locator),
        revision_id=revision_id,
        revision_number=revision_number,
    )


class TestBuildAad:
    def test_deterministic(self) -> None:
        a = build_aad(_ctx())
        b = build_aad(_ctx())
        assert a == b

    def test_different_revision_differs(self) -> None:
        a = build_aad(_ctx(revision_id=_UUID_D, revision_number=1))
        b = build_aad(_ctx(revision_id=_UUID_E, revision_number=2))
        assert a != b

    def test_different_envelope_differs(self) -> None:
        a = build_aad(_ctx(envelope_id=_UUID_A))
        b = build_aad(_ctx(envelope_id=_UUID_B))
        assert a != b

    def test_different_locator_differs(self) -> None:
        a = build_aad(_ctx(locator=b"\x01" * 32))
        b = build_aad(_ctx(locator=b"\x02" * 32))
        assert a != b

    def test_returns_bytes(self) -> None:
        result = build_aad(_ctx())
        assert isinstance(result, bytes)
