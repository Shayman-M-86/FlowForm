"""Pydantic value models and key-material type labels for crypto operations.

Key labels (all NewType over bytes — type-checker only, no runtime validation):

    PlaintextSurveyKey   — unwrapped survey key, usable for wrapping session keys
    WrappedSurveyKey     — KMS-encrypted survey key, stored in DB
    PlaintextSessionKey  — unwrapped session DEK, usable for answer encryption
    WrappedSessionKey    — survey-key-encrypted session DEK, stored in DB
    SessionLocator       — pseudonymous session locator, stored in response DB
    AnswerLocator        — pseudonymous answer locator, stored in response DB
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
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
from app.schema.orm.core.submission_session import SessionRef

# --- Key-material labels (NewType over bytes) ---

PlaintextSurveyKey = NewType("PlaintextSurveyKey", bytes)
WrappedSurveyKey = NewType("WrappedSurveyKey", bytes)
PlaintextSessionKey = NewType("PlaintextSessionKey", bytes)
WrappedSessionKey = NewType("WrappedSessionKey", bytes)
SessionLocator = NewType("SessionLocator", bytes)
AnswerLocator = NewType("AnswerLocator", bytes)

SurveyKeyResolver = Callable[[], PlaintextSurveyKey]
SessionKeyResolver = Callable[[], PlaintextSessionKey]

_CRYPTO_VERSION = 1


class NewSessionKey(CryptoValueModel):
    """Freshly created session key: plaintext for immediate use + wrapped for storage."""

    plaintext_key: PlaintextSessionKey = Field(repr=False)
    wrapped_key: WrappedSessionKey = Field(repr=False)


class NewSessionLocator(CryptoValueModel):
    """Locator material for a brand-new session."""

    linkage_key_version: PositiveVersion
    session_locator: SessionLocator = Field(min_length=1, repr=False)


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
class AnswerContext:
    """AAD context shared by current-answer encrypt and decrypt operations."""

    dek: PlaintextSessionKey
    crypto_version: int
    envelope_id: UUID
    answer_locator: AnswerLocator


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
    session_locator: SessionLocator


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Validated session state shared by public submission actions.

    This is intentionally scalar/id oriented so it is safe to cache and pass
    between service actions without carrying ORM rows across transaction
    boundaries.
    """

    session_ref: SessionRef
    session_locator: SessionLocator
    envelope_id: UUID
    linkage_key: LinkageKey
    crypto_version: int = _CRYPTO_VERSION
    loaded_from_cache: bool = False

    @property
    def session_id(self) -> UUID:
        return self.session_ref.id

    @property
    def project_id(self) -> int:
        return self.session_ref.project_id

    @property
    def survey_id(self) -> int:
        return self.session_ref.survey_id

    @property
    def survey_version_id(self) -> int:
        return self.session_ref.survey_version_id

    @property
    def expires_at(self) -> datetime:
        return self.session_ref.expires_at

    @property
    def browser_session_token_hash(self) -> bytes:
        return self.session_ref.browser_session_token_hash

    @property
    def session_dek_context(self) -> SessionDEKContext:
        return SessionDEKContext(
            session_id=self.session_id,
            crypto_version=self.crypto_version,
            project_id=self.project_id,
            survey_id=self.survey_id,
            session_locator=self.session_locator,
        )
