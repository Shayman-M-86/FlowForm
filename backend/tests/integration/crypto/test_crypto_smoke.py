"""Local-only smoke tests for crypto primitives."""

from __future__ import annotations

import os
import uuid

from pydantic import TypeAdapter

from app.cache import LockedTTLCache
from app.crypto._internal.aad import build_session_dek_wrap_aad
from app.crypto._internal.locators import derive_session_locator
from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.payload import build_plaintext_payload, parse_plaintext_payload
from app.crypto._internal.wrapping import (
    decrypt_answer,
    encrypt_answer,
    unwrap_session_key,
    wrap_session_key,
)
from app.crypto.models import (
    PlaintextSessionKey,
    PlaintextSurveyKey,
    SessionDEKContext,
    SessionLocator,
)
from app.schema.models.survey_document.answers import AnswerData
from app.schema.types import ProjectId, SubmissionSessionId, SurveyFieldUuid, SurveyId


class TestLocalCryptoRoundTrip:
    """Full round-trip using local-only primitives (tiers 2 and 3)."""

    def test_session_key_wrap_unwrap(self) -> None:
        survey_key = PlaintextSurveyKey(os.urandom(32))
        session_key = PlaintextSessionKey(os.urandom(32))

        context = SessionDEKContext(
            session_id=TypeAdapter(SubmissionSessionId).validate_python(uuid.uuid4()),
            crypto_version=1,
            project_id=TypeAdapter(ProjectId).validate_python(1),
            survey_id=TypeAdapter(SurveyId).validate_python(1),
            session_locator=SessionLocator(os.urandom(32)),
        )
        aad = build_session_dek_wrap_aad(context)

        wrapped = wrap_session_key(plaintext_key=session_key, survey_key=survey_key, aad=aad)
        assert wrapped != session_key

        unwrapped = unwrap_session_key(wrapped_key=wrapped, survey_key=survey_key, aad=aad)
        assert unwrapped == session_key

    def test_answer_encrypt_decrypt_round_trip(self) -> None:
        plaintext_dek = PlaintextSessionKey(os.urandom(32))
        field_uuid = TypeAdapter(SurveyFieldUuid).validate_python(uuid.uuid4())

        payload_bytes = build_plaintext_payload(
            field_uuid=field_uuid,
            answer=TypeAdapter(AnswerData).validate_python(
                {"state": "answered", "answer_spec": {"type": "string", "required": True}, "answer_value": "yes"}
            ),
        )
        nonce = generate_nonce()
        aad = b"test-aad-binding"
        ciphertext = encrypt_answer(payload_bytes, plaintext_dek, nonce, aad)

        decrypted = decrypt_answer(ciphertext, plaintext_dek, nonce, aad)
        parsed = parse_plaintext_payload(decrypted)
        assert parsed.field_uuid == field_uuid
        assert parsed.state == "answered"
        assert parsed.state == "answered"
        assert parsed.answer_value == "yes"

    def test_session_locator_deterministic(self) -> None:
        session_id = uuid.uuid4()
        secret = b"\xaa" * 32

        loc1 = derive_session_locator(TypeAdapter(SubmissionSessionId).validate_python(session_id), secret)
        loc2 = derive_session_locator(TypeAdapter(SubmissionSessionId).validate_python(session_id), secret)

        assert loc1 == loc2
        assert len(loc1) == 32
        assert loc1 != session_id.bytes

    def test_dek_cache_round_trip(self) -> None:
        session_locator = os.urandom(32)
        plaintext_dek = os.urandom(32)

        cache: LockedTTLCache[bytes] = LockedTTLCache(
            name="test_session_dek",
            maxsize=16,
            ttl_seconds=60,
        )

        assert cache.get(session_locator) is None
        cache.put(session_locator, plaintext_dek)
        assert cache.get(session_locator) == plaintext_dek

        cache.evict(session_locator)
        assert cache.get(session_locator) is None
