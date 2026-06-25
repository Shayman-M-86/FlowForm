"""Smoke test: full crypto round-trip against real AWS infrastructure."""

from __future__ import annotations

import base64
import json
import os
import uuid
from typing import Any

import pytest

from app.cache import LockedTTLCache
from app.crypto.aes_gcm import decrypt_answer, encrypt_answer
from app.crypto.kms import unwrap_dek, wrap_dek
from app.crypto.locators import derive_session_locator
from app.crypto.nonces import generate_nonce
from app.crypto.payload import build_plaintext_payload, parse_plaintext_payload
from app.crypto.secrets import get_linkage_secret


def _encryption_configured() -> bool:
    return bool(os.environ.get("FLOWFORM_ENCRYPTION_KMS_KEY_ARN"))


skip_no_aws = pytest.mark.skipif(
    not _encryption_configured(),
    reason="FLOWFORM_ENCRYPTION_* env vars not set",
)


def _decode_linkage_secret(secret_string: str) -> bytes:
    data: Any = json.loads(secret_string)
    assert isinstance(data, dict)
    secret_b64 = data["secret_b64"]
    assert isinstance(secret_b64, str)
    return base64.b64decode(secret_b64)


@skip_no_aws
class TestCryptoSmoke:
    """End-to-end crypto round-trip against real KMS and Secrets Manager."""

    def test_crypto_smoke_round_trip(self, settings) -> None:
        enc = settings.flowform.encryption
        assert enc is not None, "EncryptionSettings not loaded"

        region = enc.aws_region
        access_key_id = enc.aws_access_key_id
        secret_access_key = enc.aws_secret_access_key

        # 1. Fetch linkage secret
        linkage_secret = get_linkage_secret(
            enc.linkage_secret_arn,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        linkage_secret_bytes = _decode_linkage_secret(linkage_secret.secret_string)
        assert len(linkage_secret_bytes) == 32

        # 2. Derive a session locator
        core_session_id = uuid.uuid4()
        session_locator = derive_session_locator(core_session_id, linkage_secret_bytes)
        assert len(session_locator) == 32

        # 3. Generate a DEK (32 bytes for AES-256)
        plaintext_dek = os.urandom(32)

        # 4. Wrap DEK with KMS
        encryption_context = {"session_locator": session_locator.hex()}
        wrapped = wrap_dek(
            plaintext_dek,
            enc.kms_key_arn,
            encryption_context,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        assert wrapped != plaintext_dek

        # 5. Unwrap DEK
        unwrapped = unwrap_dek(
            wrapped,
            enc.kms_key_arn,
            encryption_context,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        assert unwrapped == plaintext_dek

        # 6. Build a plaintext payload and encrypt
        question_node_id = uuid.uuid4()
        payload_bytes = build_plaintext_payload(
            payload_version=1,
            question_node_id=question_node_id,
            answer_state="answered",
            answer_value={"choice": "option_a"},
        )
        nonce = generate_nonce()
        aad = b"test-aad-binding"
        ciphertext = encrypt_answer(payload_bytes, plaintext_dek, nonce, aad)

        # 7. Decrypt and verify round-trip
        decrypted = decrypt_answer(ciphertext, plaintext_dek, nonce, aad)
        parsed = parse_plaintext_payload(decrypted)
        assert parsed["question_node_id"] == question_node_id
        assert parsed["answer_state"] == "answered"
        assert parsed["answer_value"] == {"choice": "option_a"}

    def test_dek_cache_with_real_kms(self, settings) -> None:
        enc = settings.flowform.encryption
        assert enc is not None

        region = enc.aws_region
        access_key_id = enc.aws_access_key_id
        secret_access_key = enc.aws_secret_access_key

        plaintext_dek = os.urandom(32)
        encryption_context = {"test": "cache"}

        wrapped = wrap_dek(
            plaintext_dek,
            enc.kms_key_arn,
            encryption_context,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )

        session_locator = os.urandom(32)
        cache: LockedTTLCache[bytes] = LockedTTLCache(
            name="test_session_dek",
            maxsize=16,
            ttl_seconds=60,
        )

        # Cache miss → unwrap via KMS
        assert cache.get(session_locator) is None
        unwrapped = unwrap_dek(
            wrapped,
            enc.kms_key_arn,
            encryption_context,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        cache.put(session_locator, unwrapped)

        # Cache hit
        assert cache.get(session_locator) == plaintext_dek

        # Eviction
        cache.evict(session_locator)
        assert cache.get(session_locator) is None
