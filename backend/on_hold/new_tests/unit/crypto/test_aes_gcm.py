"""Contract tests for AES-GCM answer encryption primitives."""

from __future__ import annotations

import os

import pytest

from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.wrapping import DecryptionError, decrypt_answer, encrypt_answer
from app.crypto.models import PlaintextSessionKey


def _session_key() -> PlaintextSessionKey:
    return PlaintextSessionKey(os.urandom(32))


def test_encrypt_answer_returns_ciphertext_bytes() -> None:
    """Encryption should return bytes that do not expose plaintext directly."""
    plaintext = b'{"question_node_id": "abc"}'

    ciphertext = encrypt_answer(
        plaintext=plaintext,
        dek=_session_key(),
        nonce=generate_nonce(),
        aad=b"context",
    )

    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext


def test_decrypt_answer_round_trips_with_same_key_nonce_and_aad() -> None:
    """A payload encrypted with one context should decrypt with the same context."""
    dek = _session_key()
    plaintext = b'{"answer_value": {"selected": ["option-1"]}}'
    nonce = generate_nonce()
    aad = b"context"

    ciphertext = encrypt_answer(plaintext, dek, nonce, aad)

    assert decrypt_answer(ciphertext, dek, nonce, aad) == plaintext


def test_decrypt_answer_rejects_wrong_key() -> None:
    """Changing the DEK should invalidate the ciphertext."""
    nonce = generate_nonce()
    aad = b"context"
    ciphertext = encrypt_answer(b"secret", _session_key(), nonce, aad)

    with pytest.raises(DecryptionError):
        decrypt_answer(ciphertext, _session_key(), nonce, aad)


def test_decrypt_answer_rejects_wrong_aad() -> None:
    """Changing AAD should invalidate the ciphertext."""
    dek = _session_key()
    nonce = generate_nonce()
    ciphertext = encrypt_answer(b"secret", dek, nonce, b"aad-1")

    with pytest.raises(DecryptionError):
        decrypt_answer(ciphertext, dek, nonce, b"aad-2")


def test_decrypt_answer_rejects_tampered_ciphertext() -> None:
    """Changing ciphertext bytes should fail authentication."""
    dek = _session_key()
    nonce = generate_nonce()
    aad = b"context"
    ciphertext = encrypt_answer(b"secret", dek, nonce, aad)
    tampered = bytes([ciphertext[0] ^ 0x01, *ciphertext[1:]])

    with pytest.raises(DecryptionError):
        decrypt_answer(tampered, dek, nonce, aad)


def test_decrypt_answer_rejects_tampered_nonce() -> None:
    """Changing nonce bytes should fail authentication."""
    dek = _session_key()
    nonce = generate_nonce()
    aad = b"context"
    ciphertext = encrypt_answer(b"secret", dek, nonce, aad)
    tampered_nonce = bytes([nonce[0] ^ 0x01, *nonce[1:]])

    with pytest.raises(DecryptionError):
        decrypt_answer(ciphertext, dek, tampered_nonce, aad)
