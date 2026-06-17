"""Tests for AAD construction."""

from app.crypto.aad import build_aad


class TestBuildAad:
    def test_deterministic(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, 100, 200, locator, 300, 1)
        b = build_aad(1, 100, 200, locator, 300, 1)
        assert a == b

    def test_different_revision_differs(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, 100, 200, locator, 300, 1)
        b = build_aad(1, 100, 200, locator, 301, 2)
        assert a != b

    def test_different_envelope_differs(self) -> None:
        locator = b"\x01" * 32
        a = build_aad(1, 100, 200, locator, 300, 1)
        b = build_aad(1, 101, 200, locator, 300, 1)
        assert a != b

    def test_different_locator_differs(self) -> None:
        a = build_aad(1, 100, 200, b"\x01" * 32, 300, 1)
        b = build_aad(1, 100, 200, b"\x02" * 32, 300, 1)
        assert a != b

    def test_returns_bytes(self) -> None:
        result = build_aad(1, 100, 200, b"\x01" * 32, 300, 1)
        assert isinstance(result, bytes)
