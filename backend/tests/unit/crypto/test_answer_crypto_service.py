"""Unit tests for answer-level encrypt/decrypt round-trips."""

from __future__ import annotations

import os
import uuid
from uuid import UUID

import pytest

from app.crypto._internal.wrapping import DecryptionError
from app.crypto.answers import decrypt_answer_revision, encrypt_answer_revision
from app.crypto.models import (
    AnswerLocator,
    PlaintextSessionKey,
    RevisionContext,
)

Q1 = UUID("00000000-0000-0000-0000-000000000001")
Q5 = UUID("00000000-0000-0000-0000-000000000005")


def _dek() -> PlaintextSessionKey:
    return PlaintextSessionKey(os.urandom(32))


def _revision_ctx(dek: PlaintextSessionKey) -> RevisionContext:
    return RevisionContext(
        dek=dek,
        crypto_version=1,
        envelope_id=uuid.uuid4(),
        answer_id=uuid.uuid4(),
        answer_locator=AnswerLocator(os.urandom(32)),
        revision_id=uuid.uuid4(),
        revision_number=1,
    )


class TestEncrypt:
    def test_returns_encrypted_answer(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        result = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        assert isinstance(result.ciphertext, bytes)
        assert len(result.ciphertext) > 0
        assert isinstance(result.nonce, bytes)
        assert len(result.nonce) == 12

    def test_different_calls_produce_different_nonces(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        a = encrypt_answer_revision(
            context=ctx, question_node_id=Q1, answer_state="answered", answer_value={"value": "yes"},
        )
        ctx2 = RevisionContext(
            dek=dek,
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_id=ctx.answer_id,
            answer_locator=ctx.answer_locator,
            revision_id=uuid.uuid4(),
            revision_number=2,
        )
        b = encrypt_answer_revision(
            context=ctx2, question_node_id=Q1, answer_state="answered", answer_value={"value": "yes"},
        )
        assert a.nonce != b.nonce

    def test_none_answer_value(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        result = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="cleared",
            answer_value=None,
        )
        assert isinstance(result.ciphertext, bytes)


class TestDecrypt:
    def test_round_trip(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        decrypted = decrypt_answer_revision(
            ciphertext=encrypted.ciphertext,
            nonce=encrypted.nonce,
            context=ctx,
        )
        assert decrypted.question_node_id == Q1
        assert decrypted.answer_state == "answered"
        assert decrypted.answer_value == {"value": "yes"}

    def test_round_trip_complex_value(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        value = {"selected": [1, 2, 3], "other": "text"}
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q5,
            answer_state="answered",
            answer_value=value,
        )
        decrypted = decrypt_answer_revision(
            ciphertext=encrypted.ciphertext,
            nonce=encrypted.nonce,
            context=ctx,
        )
        assert decrypted.answer_value == value

    def test_round_trip_none_value(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="cleared",
            answer_value=None,
        )
        decrypted = decrypt_answer_revision(
            ciphertext=encrypted.ciphertext,
            nonce=encrypted.nonce,
            context=ctx,
        )
        assert decrypted.answer_value is None
        assert decrypted.answer_state == "cleared"

    def test_wrong_dek_raises(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        wrong_ctx = RevisionContext(
            dek=_dek(),
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_id=ctx.answer_id,
            answer_locator=ctx.answer_locator,
            revision_id=ctx.revision_id,
            revision_number=ctx.revision_number,
        )
        with pytest.raises(DecryptionError):
            decrypt_answer_revision(
                ciphertext=encrypted.ciphertext,
                nonce=encrypted.nonce,
                context=wrong_ctx,
            )

    def test_wrong_aad_raises(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        wrong_ctx = RevisionContext(
            dek=dek,
            crypto_version=ctx.crypto_version,
            envelope_id=uuid.uuid4(),
            answer_id=ctx.answer_id,
            answer_locator=ctx.answer_locator,
            revision_id=ctx.revision_id,
            revision_number=ctx.revision_number,
        )
        with pytest.raises(DecryptionError):
            decrypt_answer_revision(
                ciphertext=encrypted.ciphertext,
                nonce=encrypted.nonce,
                context=wrong_ctx,
            )

    def test_tampered_ciphertext_raises(self) -> None:
        dek = _dek()
        ctx = _revision_ctx(dek)
        encrypted = encrypt_answer_revision(
            context=ctx,
            question_node_id=Q1,
            answer_state="answered",
            answer_value={"value": "yes"},
        )
        tampered = bytes([b ^ 0xFF for b in encrypted.ciphertext])
        with pytest.raises(DecryptionError):
            decrypt_answer_revision(
                ciphertext=tampered,
                nonce=encrypted.nonce,
                context=ctx,
            )
