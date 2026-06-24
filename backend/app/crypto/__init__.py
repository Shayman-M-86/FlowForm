"""Cryptographic building blocks for session response encryption."""

from app.crypto.aad import build_aad
from app.crypto.aes_gcm import DecryptionError, decrypt_answer, encrypt_answer
from app.crypto.dek_cache import DekCache
from app.crypto.errors import (
    KmsError,
    LinkageKeyError,
    LinkageKeyUnavailableError,
    LinkageKeyVersionUnavailableError,
    LinkageSecretError,
    SessionDEKUnavailableError,
    SurveyBranchKeyUnavailableError,
)
from app.crypto.kms import unwrap_dek, wrap_dek
from app.crypto.locators import derive_answer_locator, derive_session_locator
from app.crypto.nonces import generate_nonce
from app.crypto.payload import (
    PayloadDecodeError,
    build_plaintext_payload,
    parse_plaintext_payload,
)
from app.crypto.secrets import SecretValue, get_linkage_secret
from app.crypto.services import (
    SURVEY_KMS_CONTEXT_VERSION,
    AnswerCryptoService,
    DecryptedAnswer,
    DecryptedAnswerPayload,
    EncryptedAnswer,
    EncryptedAnswerPayload,
    LinkageKey,
    LinkageKeyService,
    LocatorService,
    NewSessionDEK,
    NewSessionLocator,
    SessionDEKService,
    SurveyBranchKeyService,
    build_survey_kms_context,
)

__all__ = [
    "SURVEY_KMS_CONTEXT_VERSION",
    "AnswerCryptoService",
    "DecryptedAnswer",
    "DecryptedAnswerPayload",
    "DecryptionError",
    "DekCache",
    "EncryptedAnswer",
    "EncryptedAnswerPayload",
    "KmsError",
    "LinkageKey",
    "LinkageKeyError",
    "LinkageKeyService",
    "LinkageKeyUnavailableError",
    "LinkageKeyVersionUnavailableError",
    "LinkageSecretError",
    "LocatorService",
    "NewSessionDEK",
    "NewSessionLocator",
    "PayloadDecodeError",
    "SecretValue",
    "SessionDEKService",
    "SessionDEKUnavailableError",
    "SurveyBranchKeyService",
    "SurveyBranchKeyUnavailableError",
    "build_aad",
    "build_plaintext_payload",
    "build_survey_kms_context",
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
