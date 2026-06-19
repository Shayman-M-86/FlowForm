"""Unit tests for AnswerCryptoService."""

from __future__ import annotations

import os

import pytest

from app.crypto.aes_gcm import DecryptionError
from app.crypto.payload import PayloadDecodeError
from app.crypto.services.answer_crypto_service import (
    AnswerCryptoService,
    DecryptedAnswer,
    EncryptedAnswer,
)


def _dek() -> bytes:
    return os.urandom(32)


def _aad() -> bytes:
    return os.urandom(64)


class TestEncrypt:
    def test_returns_encrypted_answer(self) -> None:
        svc = AnswerCryptoService()
        result = svc.encrypt(_dek(), "q-1", "answered", "yes", _aad())
        assert isinstance(result, EncryptedAnswer)
        assert isinstance(result.ciphertext, bytes)
        assert len(result.ciphertext) > 0
        assert isinstance(result.nonce, bytes)
        assert len(result.nonce) == 12

    def test_different_calls_produce_different_nonces(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        a = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        b = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        assert a.nonce != b.nonce

    def test_different_calls_produce_different_ciphertext(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        a = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        b = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        assert a.ciphertext != b.ciphertext

    def test_none_answer_value(self) -> None:
        svc = AnswerCryptoService()
        result = svc.encrypt(_dek(), "q-1", "skipped", None, _aad())
        assert isinstance(result, EncryptedAnswer)


class TestDecrypt:
    def test_round_trip(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        encrypted = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        decrypted = svc.decrypt(dek, encrypted.ciphertext, encrypted.nonce, aad)
        assert isinstance(decrypted, DecryptedAnswer)
        assert decrypted.question_node_id == "q-1"
        assert decrypted.answer_state == "answered"
        assert decrypted.answer_value == "yes"

    def test_round_trip_complex_value(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        value = {"selected": [1, 2, 3], "other": "text"}
        encrypted = svc.encrypt(dek, "q-5", "answered", value, aad)
        decrypted = svc.decrypt(dek, encrypted.ciphertext, encrypted.nonce, aad)
        assert decrypted.answer_value == value

    def test_round_trip_none_value(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        encrypted = svc.encrypt(dek, "q-1", "skipped", None, aad)
        decrypted = svc.decrypt(dek, encrypted.ciphertext, encrypted.nonce, aad)
        assert decrypted.answer_value is None
        assert decrypted.answer_state == "skipped"

    def test_wrong_dek_raises(self) -> None:
        svc = AnswerCryptoService()
        aad = _aad()
        encrypted = svc.encrypt(_dek(), "q-1", "answered", "yes", aad)
        with pytest.raises(DecryptionError):
            svc.decrypt(_dek(), encrypted.ciphertext, encrypted.nonce, aad)

    def test_wrong_aad_raises(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        encrypted = svc.encrypt(dek, "q-1", "answered", "yes", _aad())
        with pytest.raises(DecryptionError):
            svc.decrypt(dek, encrypted.ciphertext, encrypted.nonce, _aad())

    def test_tampered_ciphertext_raises(self) -> None:
        svc = AnswerCryptoService()
        dek = _dek()
        aad = _aad()
        encrypted = svc.encrypt(dek, "q-1", "answered", "yes", aad)
        tampered = bytes([b ^ 0xFF for b in encrypted.ciphertext])
        with pytest.raises(DecryptionError):
            svc.decrypt(dek, tampered, encrypted.nonce, aad)
