"""Tests for nonce generation."""

from app.crypto._internal.nonces import generate_nonce


class TestGenerateNonce:
    def test_returns_12_bytes(self) -> None:
        nonce = generate_nonce()
        assert isinstance(nonce, bytes)
        assert len(nonce) == 12

    def test_unique(self) -> None:
        nonces = {generate_nonce() for _ in range(100)}
        assert len(nonces) == 100
