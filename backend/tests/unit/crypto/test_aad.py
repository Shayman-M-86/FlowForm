"""Tests for AAD construction."""

import uuid

from app.crypto.aad import build_aad

_UUID_A = uuid.UUID("00000000-0000-0000-0000-000000000064")
_UUID_B = uuid.UUID("00000000-0000-0000-0000-000000000065")
_UUID_C = uuid.UUID("00000000-0000-0000-0000-0000000000c8")
_UUID_D = uuid.UUID("00000000-0000-0000-0000-00000000012c")
_UUID_E = uuid.UUID("00000000-0000-0000-0000-00000000012d")


class TestBuildAad:
    def test_deterministic(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, _UUID_A, _UUID_C, locator, _UUID_D, 1)
        b = build_aad(1, _UUID_A, _UUID_C, locator, _UUID_D, 1)
        assert a == b

    def test_different_revision_differs(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, _UUID_A, _UUID_C, locator, _UUID_D, 1)
        b = build_aad(1, _UUID_A, _UUID_C, locator, _UUID_E, 2)
        assert a != b

    def test_different_envelope_differs(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, _UUID_A, _UUID_C, locator, _UUID_D, 1)
        b = build_aad(1, _UUID_B, _UUID_C, locator, _UUID_D, 1)
        assert a != b

    def test_different_locator_differs(self) -> None:
        a = build_aad(1, _UUID_A, _UUID_C, b"\x01" * 32, _UUID_D, 1)
        b = build_aad(1, _UUID_A, _UUID_C, b"\x02" * 32, _UUID_D, 1)
        assert a != b

    def test_returns_bytes(self) -> None:
        result = build_aad(1, _UUID_A, _UUID_C, b"\x01" * 32, _UUID_D, 1)
        assert isinstance(result, bytes)
