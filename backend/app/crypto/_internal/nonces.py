"""Cryptographically random nonce generation."""

import os

_NONCE_LENGTH = 12


def generate_nonce() -> bytes:
    """Generate a 12-byte cryptographically random nonce for AES-GCM."""
    return os.urandom(_NONCE_LENGTH)
