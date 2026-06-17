"""Tests for AES-256-GCM encrypt/decrypt."""

import os

import pytest

from app.crypto.aes_gcm import DecryptionError, decrypt_answer, encrypt_answer


def _dek() -> bytes:
    return os.urandom(32)


def _nonce() -> bytes:
    return os.urandom(12)


class TestEncryptDecryptRoundTrip:
    def test_round_trip(self) -> None:
        dek = _dek()
        nonce = _nonce()
        aad = b"context-data"
        plaintext = b'{"v":1,"question_node_id":"q1","answer_state":"answered","answer_value":"yes"}'

        ciphertext = encrypt_answer(plaintext, dek, nonce, aad)
        result = decrypt_answer(ciphertext, dek, nonce, aad)
        assert result == plaintext

    def test_ciphertext_differs_from_plaintext(self) -> None:
        dek = _dek()
        nonce = _nonce()
        plaintext = b"hello"
        ciphertext = encrypt_answer(plaintext, dek, nonce, b"aad")
        assert ciphertext != plaintext


class TestDecryptionFailures:
    def test_wrong_aad_raises(self) -> None:
        dek = _dek()
        nonce = _nonce()
        ciphertext = encrypt_answer(b"data", dek, nonce, b"aad-1")
        with pytest.raises(DecryptionError):
            decrypt_answer(ciphertext, dek, nonce, b"aad-2")

    def test_wrong_dek_raises(self) -> None:
        nonce = _nonce()
        ciphertext = encrypt_answer(b"data", _dek(), nonce, b"aad")
        with pytest.raises(DecryptionError):
            decrypt_answer(ciphertext, _dek(), nonce, b"aad")

    def test_tampered_ciphertext_raises(self) -> None:
        dek = _dek()
        nonce = _nonce()
        ciphertext = bytearray(encrypt_answer(b"data", dek, nonce, b"aad"))
        ciphertext[0] ^= 0xFF
        with pytest.raises(DecryptionError):
            decrypt_answer(bytes(ciphertext), dek, nonce, b"aad")

    def test_wrong_nonce_raises(self) -> None:
        dek = _dek()
        ciphertext = encrypt_answer(b"data", dek, _nonce(), b"aad")
        with pytest.raises(DecryptionError):
            decrypt_answer(ciphertext, dek, _nonce(), b"aad")


class TestKeyValidation:
    def test_short_dek_rejected(self) -> None:
        with pytest.raises(ValueError, match="DEK must be 32 bytes"):
            encrypt_answer(b"data", b"short", _nonce(), b"aad")

    def test_short_dek_rejected_on_decrypt(self) -> None:
        with pytest.raises(ValueError, match="DEK must be 32 bytes"):
            decrypt_answer(b"data", b"short", _nonce(), b"aad")
