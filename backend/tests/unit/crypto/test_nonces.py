"""Tests for nonce generation."""

from app.crypto.nonces import generate_nonce


class TestGenerateNonce:
    def test_length_is_12_bytes(self) -> None:
        assert len(generate_nonce()) == 12

    def test_uniqueness_across_1000_calls(self) -> None:
        nonces = {generate_nonce() for _ in range(1000)}
        assert len(nonces) == 1000
