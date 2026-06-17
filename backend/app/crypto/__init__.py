"""Cryptographic building blocks for session response encryption."""

from app.crypto.aad import build_aad
from app.crypto.aes_gcm import DecryptionError, decrypt_answer, encrypt_answer
from app.crypto.locators import derive_answer_locator, derive_session_locator
from app.crypto.nonces import generate_nonce
from app.crypto.payload import (
    PayloadDecodeError,
    build_plaintext_payload,
    parse_plaintext_payload,
)

__all__ = [
    "DecryptionError",
    "PayloadDecodeError",
    "build_aad",
    "build_plaintext_payload",
    "decrypt_answer",
    "derive_answer_locator",
    "derive_session_locator",
    "encrypt_answer",
    "generate_nonce",
    "parse_plaintext_payload",
]
