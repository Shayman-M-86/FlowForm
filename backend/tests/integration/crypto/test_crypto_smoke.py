"""Local-only smoke tests for crypto primitives."""

from __future__ import annotations

import os
import uuid

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


class TestLocalCryptoRoundTrip:
    """Full round-trip using local-only primitives (tiers 2 and 3)."""

    def test_session_key_wrap_unwrap(self) -> None:
        survey_key = PlaintextSurveyKey(os.urandom(32))
        session_key = PlaintextSessionKey(os.urandom(32))

        context = SessionDEKContext(
            session_id=uuid.uuid4(),
            crypto_version=1,
            project_id=1,
            survey_id=1,
            session_locator=SessionLocator(os.urandom(32)),
        )
        aad = build_session_dek_wrap_aad(context)

        wrapped = wrap_session_key(plaintext_key=session_key, survey_key=survey_key, aad=aad)
        assert wrapped != session_key

        unwrapped = unwrap_session_key(wrapped_key=wrapped, survey_key=survey_key, aad=aad)
        assert unwrapped == session_key

    def test_answer_encrypt_decrypt_round_trip(self) -> None:
        plaintext_dek = PlaintextSessionKey(os.urandom(32))
        question_node_id = uuid.uuid4()

        payload_bytes = build_plaintext_payload(
            question_node_id=question_node_id,
            answer_state="answered",
            answer_value={"choice": "option_a"},
        )
        nonce = generate_nonce()
        aad = b"test-aad-binding"
        ciphertext = encrypt_answer(payload_bytes, plaintext_dek, nonce, aad)

        decrypted = decrypt_answer(ciphertext, plaintext_dek, nonce, aad)
        parsed = parse_plaintext_payload(decrypted)
        assert parsed.question_node_id == question_node_id
        assert parsed.answer_state == "answered"
        assert parsed.answer_value == {"choice": "option_a"}

    def test_session_locator_deterministic(self) -> None:
        session_id = uuid.uuid4()
        secret = b"\xaa" * 32

        loc1 = derive_session_locator(session_id, secret)
        loc2 = derive_session_locator(session_id, secret)

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
