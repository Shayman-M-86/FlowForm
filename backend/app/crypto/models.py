"""Pydantic value models and key-material type labels for crypto operations.

Key labels (all NewType over bytes — type-checker only, no runtime validation):

    PlaintextSurveyKey   — unwrapped survey key, usable for wrapping session keys
    WrappedSurveyKey     — KMS-encrypted survey key, stored in DB
    PlaintextSessionKey  — unwrapped session DEK, usable for answer encryption
    WrappedSessionKey    — survey-key-encrypted session DEK, stored in DB
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NewType, Self
from uuid import UUID

from pydantic import Field

from app.crypto._internal.models import (
    CryptoValueModel,
    LinkageSecret,
    LinkageSecretPayload,
    NonEmptyStr,
    PositiveVersion,
    SecretValue,
)

# --- Key-material labels (NewType over bytes) ---

PlaintextSurveyKey = NewType("PlaintextSurveyKey", bytes)
WrappedSurveyKey = NewType("WrappedSurveyKey", bytes)
PlaintextSessionKey = NewType("PlaintextSessionKey", bytes)
WrappedSessionKey = NewType("WrappedSessionKey", bytes)

SurveyKeyResolver = Callable[[], PlaintextSurveyKey]


class NewSessionKey(CryptoValueModel):
    """Freshly created session key: plaintext for immediate use + wrapped for storage."""

    plaintext_key: PlaintextSessionKey = Field(repr=False)
    wrapped_key: WrappedSessionKey = Field(repr=False)


class NewSessionLocator(CryptoValueModel):
    """Locator material for a brand-new session."""

    linkage_key_version: PositiveVersion
    session_locator: bytes = Field(min_length=1, repr=False)


class LinkageKey(CryptoValueModel):
    """A versioned linkage secret."""

    version: PositiveVersion
    secret: LinkageSecret
    aws_version_id: NonEmptyStr

    @classmethod
    def from_secret_value(cls, secret: SecretValue) -> Self:
        payload = LinkageSecretPayload.model_validate_json(secret.secret_string)

        return cls(
            version=payload.version,
            secret=payload.secret,
            aws_version_id=secret.version_id,
        )


@dataclass(frozen=True, slots=True)
class RevisionContext:
    """AAD context shared by encrypt and decrypt operations."""

    dek: PlaintextSessionKey
    crypto_version: int
    envelope_id: UUID
    answer_id: UUID
    answer_locator: bytes
    revision_id: UUID
    revision_number: int


@dataclass(frozen=True, slots=True)
class EncryptedRevision:
    """A revision's ciphertext paired with its AAD context for decryption."""

    ciphertext: bytes
    nonce: bytes
    context: RevisionContext


@dataclass(frozen=True, slots=True)
class SessionDEKContext:
    """Identity of a session, used to bind its DEK wrap to its survey.

    Carries the fields needed to build the session-DEK wrap AAD. The
    crypto layer derives the AAD internally so callers never handle it.
    """

    session_id: UUID
    crypto_version: int
    project_id: int
    survey_id: int
    session_locator: bytes
