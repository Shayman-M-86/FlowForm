from __future__ import annotations

import uuid

from app.crypto.answers import decrypt_answer_current, encrypt_answer_current
from app.crypto.models import AnswerContext, AnswerLocator, PlaintextSessionKey


def _ctx() -> AnswerContext:
    return AnswerContext(
        dek=PlaintextSessionKey(b"d" * 32),
        crypto_version=1,
        envelope_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        answer_locator=AnswerLocator(b"a" * 32),
    )


def test_encrypt_decrypt_current_answer_round_trip() -> None:
    question_node_id = uuid.uuid4()
    encrypted = encrypt_answer_current(
        context=_ctx(),
        question_node_id=question_node_id,
        answer_state="answered",
        answer_value={"value": "yes"},
    )

    decrypted = decrypt_answer_current(
        ciphertext=encrypted.ciphertext,
        nonce=encrypted.nonce,
        context=_ctx(),
    )

    assert decrypted.question_node_id == question_node_id
    assert decrypted.answer_state == "answered"
    assert decrypted.answer_value == {"value": "yes"}
