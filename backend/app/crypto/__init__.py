"""Cryptographic building blocks for session response encryption."""

from app.crypto.aad import build_aad
from app.crypto.aes_gcm import DecryptionError, decrypt_answer, encrypt_answer
from app.crypto.dek_cache import DekCache
from app.crypto.kms import KmsError, unwrap_dek, wrap_dek
from app.crypto.locators import derive_answer_locator, derive_session_locator
from app.crypto.nonces import generate_nonce
from app.crypto.payload import (
    PayloadDecodeError,
    build_plaintext_payload,
    parse_plaintext_payload,
)
from app.crypto.secrets import LinkageSecretError, get_linkage_secret

__all__ = [
    "DecryptionError",
    "DekCache",
    "KmsError",
    "LinkageSecretError",
    "PayloadDecodeError",
    "build_aad",
    "build_plaintext_payload",
    "decrypt_answer",
    "derive_answer_locator",
    "derive_session_locator",
    "encrypt_answer",
    "generate_nonce",
    "get_linkage_secret",
    "parse_plaintext_payload",
    "unwrap_dek",
    "wrap_dek",
]
