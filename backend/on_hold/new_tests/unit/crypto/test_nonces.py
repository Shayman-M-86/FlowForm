"""Contract tests for nonce generation."""

from __future__ import annotations

from app.crypto._internal.nonces import generate_nonce


def test_generate_nonce_returns_12_bytes() -> None:
    """AES-GCM nonces should use the standard 96-bit size."""
    nonce = generate_nonce()

    assert isinstance(nonce, bytes)
    assert len(nonce) == 12


def test_generate_nonce_returns_unique_values() -> None:
    """Repeated nonce generation should not repeat in a small sample."""
    nonces = {generate_nonce() for _ in range(100)}

    assert len(nonces) == 100
