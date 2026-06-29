"""The wrap/unwrap primitives for all three key-hierarchy tiers.

Read top to bottom to follow the chain. See KEY_HIERARCHY.md.

    Tier 1  KMS            wraps the survey key       (wrap_survey_key / unwrap_survey_key)
    Tier 2  survey key     wraps the session key       (wrap_session_key / unwrap_session_key)
    Tier 3  session key    wraps the answer payload    (encrypt_answer / decrypt_answer)

Tiers 2 and 3 are the same AES-256-GCM operation; tier 1 is a KMS API call.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.crypto._internal.errors import KmsError
from app.crypto._internal.models import SESSION_DEK_WRAP_NONCE_BYTES
from app.crypto._internal.nonces import generate_nonce
from app.crypto.models import (
    PlaintextSessionKey,
    PlaintextSurveyKey,
    WrappedSessionKey,
    WrappedSurveyKey,
)

if TYPE_CHECKING:
    from mypy_boto3_kms import KMSClient

logger = logging.getLogger(__name__)


class DecryptionError(Exception):
    """Raised when decryption fails due to tampered ciphertext or AAD mismatch."""


# --- Tier 1: KMS protects the survey key ------------------------------------


def wrap_survey_key(
    plaintext_key: PlaintextSurveyKey,
    key_arn: str,
    context: dict[str, str],
    *,
    client: KMSClient | None = None,
) -> WrappedSurveyKey:
    """Encrypt a plaintext survey key with AWS KMS."""
    if client is None:
        raise ValueError("KMS client is required")

    try:
        response = client.encrypt(
            KeyId=key_arn,
            Plaintext=plaintext_key,
            EncryptionContext=context,
        )
    except Exception as exc:
        logger.error("KMS encrypt failed key_arn=%s", key_arn)
        raise KmsError("KMS encrypt failed") from exc

    return WrappedSurveyKey(response["CiphertextBlob"])


def unwrap_survey_key(
    wrapped_key: WrappedSurveyKey,
    key_arn: str,
    context: dict[str, str],
    *,
    client: KMSClient | None = None,
) -> PlaintextSurveyKey:
    """Decrypt a KMS-wrapped survey key."""
    if client is None:
        raise ValueError("KMS client is required")

    try:
        response = client.decrypt(
            KeyId=key_arn,
            CiphertextBlob=wrapped_key,
            EncryptionContext=context,
        )
    except Exception as exc:
        logger.error("KMS decrypt failed key_arn=%s", key_arn)
        raise KmsError("KMS decrypt failed") from exc

    return PlaintextSurveyKey(response["Plaintext"])


# --- Tier 2: survey key protects the session key -----------------------------


def wrap_session_key(
    *,
    plaintext_key: PlaintextSessionKey,
    survey_key: PlaintextSurveyKey,
    aad: bytes,
) -> WrappedSessionKey:
    """Encrypt a session key under a survey key. Returns nonce || ciphertext."""
    nonce = generate_nonce()
    ciphertext = AESGCM(survey_key).encrypt(nonce, plaintext_key, aad)
    return WrappedSessionKey(nonce + ciphertext)


def unwrap_session_key(
    *,
    wrapped_key: WrappedSessionKey,
    survey_key: PlaintextSurveyKey,
    aad: bytes,
) -> PlaintextSessionKey:
    """Decrypt a wrapped session key. Expects nonce || ciphertext."""
    if len(wrapped_key) <= SESSION_DEK_WRAP_NONCE_BYTES:
        raise ValueError("wrapped session key is too short to contain a nonce")

    nonce = wrapped_key[:SESSION_DEK_WRAP_NONCE_BYTES]
    ciphertext = wrapped_key[SESSION_DEK_WRAP_NONCE_BYTES:]
    return PlaintextSessionKey(AESGCM(survey_key).decrypt(nonce, ciphertext, aad))


# --- Tier 3: session key protects the answer payload -------------------------


def encrypt_answer(
    plaintext: bytes,
    dek: PlaintextSessionKey,
    nonce: bytes,
    aad: bytes,
) -> bytes:
    """Encrypt an answer payload under a session key with AES-256-GCM."""
    return AESGCM(dek).encrypt(nonce, plaintext, aad)


def decrypt_answer(
    ciphertext: bytes,
    dek: PlaintextSessionKey,
    nonce: bytes,
    aad: bytes,
) -> bytes:
    """Decrypt an answer payload under a session key.

    Raises DecryptionError on AAD mismatch or tampered ciphertext.
    """
    try:
        return AESGCM(dek).decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise DecryptionError("Decryption failed: ciphertext or AAD invalid") from exc
