"""Field identities and shared answer models survive actual authenticated encryption."""

from dataclasses import replace
from uuid import UUID

import pytest
from pydantic import TypeAdapter

from app.crypto._internal.wrapping import DecryptionError
from app.crypto.answers import decrypt_answer_current, encrypt_answer_current
from app.crypto.models import AnswerContext, AnswerLocator, PlaintextSessionKey
from app.schema.models.survey_document.answers import AnswerData
from app.schema.types import SurveyFieldUuid


def context() -> AnswerContext:
    return AnswerContext(
        dek=PlaintextSessionKey(b"d" * 32),
        crypto_version=1,
        envelope_id=UUID("11111111-1111-1111-1111-111111111111"),
        answer_locator=AnswerLocator(b"a" * 32),
    )


@pytest.mark.parametrize("state", ["answered", "cleared"])
def test_encrypt_decrypt_field_answer_round_trip(state):
    payload = {"state": state}
    if state == "answered":
        payload.update(answer_spec={"type": "integer", "required": True}, answer_value=42)
    answer = TypeAdapter(AnswerData).validate_python(payload)
    field_uuid = TypeAdapter(SurveyFieldUuid).validate_python("10000000-0000-4000-8000-000000000001")
    encrypted = encrypt_answer_current(context=context(), field_uuid=field_uuid, answer=answer)
    decrypted = decrypt_answer_current(ciphertext=encrypted.ciphertext, nonce=encrypted.nonce, context=context())
    assert decrypted.field_uuid == field_uuid and decrypted.state == state
    if decrypted.state == "answered":
        assert decrypted.answer_spec.type == "integer" and decrypted.answer_value == 42
    else:
        assert "answer_value" not in decrypted.model_dump()


def test_each_save_uses_fresh_nonce_with_same_stable_locator():
    answer = TypeAdapter(AnswerData).validate_python({"state": "cleared"})
    field_uuid = TypeAdapter(SurveyFieldUuid).validate_python("10000000-0000-4000-8000-000000000001")
    first = encrypt_answer_current(context=context(), field_uuid=field_uuid, answer=answer)
    second = encrypt_answer_current(context=context(), field_uuid=field_uuid, answer=answer)
    assert first.nonce != second.nonce and first.ciphertext != second.ciphertext
    wrong = replace(context(), answer_locator=AnswerLocator(b"b" * 32))
    with pytest.raises(DecryptionError):
        decrypt_answer_current(ciphertext=first.ciphertext, nonce=first.nonce, context=wrong)
