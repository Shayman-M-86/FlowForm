"""AES-256-GCM encrypt and decrypt for answer payloads."""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_AES_KEY_LENGTH = 32


class DecryptionError(Exception):
    """Raised when decryption fails due to tampered ciphertext or AAD mismatch."""


def encrypt_answer(plaintext: bytes, dek: bytes, nonce: bytes, aad: bytes) -> bytes:
    """Encrypt an answer payload with AES-256-GCM."""
    if len(dek) != _AES_KEY_LENGTH:
        raise ValueError(f"DEK must be {_AES_KEY_LENGTH} bytes, got {len(dek)}")
    aesgcm = AESGCM(dek)
    return aesgcm.encrypt(nonce, plaintext, aad)


def decrypt_answer(ciphertext: bytes, dek: bytes, nonce: bytes, aad: bytes) -> bytes:
    """Decrypt an answer payload with AES-256-GCM.

    Raises DecryptionError on AAD mismatch or tampered ciphertext.
    """
    if len(dek) != _AES_KEY_LENGTH:
        raise ValueError(f"DEK must be {_AES_KEY_LENGTH} bytes, got {len(dek)}")
    aesgcm = AESGCM(dek)
    try:
        return aesgcm.decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise DecryptionError("Decryption failed: ciphertext or AAD invalid") from exc
