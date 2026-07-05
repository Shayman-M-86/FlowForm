"""Tests for AES-256-GCM encrypt/decrypt."""

import os

import pytest

from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.wrapping import DecryptionError, decrypt_answer, encrypt_answer
from app.crypto.models import PlaintextSessionKey


class TestEncryptAnswer:
    def test_returns_bytes(self) -> None:
        dek = PlaintextSessionKey(os.urandom(32))
        plaintext = b"hello world"
        nonce = generate_nonce()
        aad = b"test"
        result = encrypt_answer(plaintext, dek, nonce, aad)
        assert isinstance(result, bytes)

    def test_ciphertext_differs_from_plaintext(self) -> None:
        dek = PlaintextSessionKey(os.urandom(32))
        plaintext = b"hello world"
        nonce = generate_nonce()
        aad = b"test"
        result = encrypt_answer(plaintext, dek, nonce, aad)
        assert result != plaintext


class TestDecryptAnswer:
    def test_round_trip(self) -> None:
        dek = PlaintextSessionKey(os.urandom(32))
        plaintext = b'{"question_node_id": "abc"}'
        nonce = generate_nonce()
        aad = b"context"
        ciphertext = encrypt_answer(plaintext, dek, nonce, aad)
        decrypted = decrypt_answer(ciphertext, dek, nonce, aad)
        assert decrypted == plaintext

    def test_wrong_key_raises(self) -> None:
        dek1 = PlaintextSessionKey(os.urandom(32))
        dek2 = PlaintextSessionKey(os.urandom(32))
        plaintext = b"secret"
        nonce = generate_nonce()
        aad = b"ctx"
        ciphertext = encrypt_answer(plaintext, dek1, nonce, aad)
        with pytest.raises(DecryptionError):
            decrypt_answer(ciphertext, dek2, nonce, aad)

    def test_wrong_aad_raises(self) -> None:
        dek = PlaintextSessionKey(os.urandom(32))
        plaintext = b"secret"
        nonce = generate_nonce()
        ciphertext = encrypt_answer(plaintext, dek, nonce, b"aad1")
        with pytest.raises(DecryptionError):
            decrypt_answer(ciphertext, dek, nonce, b"aad2")

    def test_tampered_ciphertext_raises(self) -> None:
        dek = PlaintextSessionKey(os.urandom(32))
        plaintext = b"secret"
        nonce = generate_nonce()
        aad = b"ctx"
        ciphertext = encrypt_answer(plaintext, dek, nonce, aad)
        tampered = bytes([b ^ 0xFF for b in ciphertext])
        with pytest.raises(DecryptionError):
            decrypt_answer(tampered, dek, nonce, aad)
