"""Pydantic value models for low-level crypto primitives."""

from __future__ import annotations

import base64
import binascii
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)

from app.schema.enums import SubmissionAnswerState

MIN_LINKAGE_SECRET_BYTES = 32
PLAINTEXT_PAYLOAD_VERSION = 1
SESSION_DEK_BYTES = 32
SESSION_DEK_WRAP_NONCE_BYTES = 12

PlaintextAnswerValue = JsonValue

PositiveVersion = Annotated[int, Field(ge=1)]
NonEmptyStr = Annotated[str, Field(min_length=1)]

SessionDEK = Annotated[
    bytes,
    Field(
        min_length=SESSION_DEK_BYTES,
        max_length=SESSION_DEK_BYTES,
        strict=True,
        repr=False,
    ),
]

WrappedSessionDEK = Annotated[
    bytes,
    Field(
        min_length=SESSION_DEK_WRAP_NONCE_BYTES + 1,
        strict=True,
        repr=False,
    ),
]

LinkageSecret = Annotated[
    bytes,
    Field(
        min_length=MIN_LINKAGE_SECRET_BYTES,
        strict=True,
        repr=False,
    ),
]


def decode_base64_bytes(value: Any) -> bytes:
    """Decode strict standard base64 text/bytes into raw bytes."""
    if isinstance(value, str):
        value = value.encode("ascii")
    elif not isinstance(value, bytes):
        raise ValueError("secret_b64 must be base64 text or bytes")

    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("secret_b64 is not valid base64") from exc


Base64LinkageSecret = Annotated[
    bytes,
    BeforeValidator(decode_base64_bytes),
    Field(
        min_length=MIN_LINKAGE_SECRET_BYTES,
        strict=True,
        repr=False,
    ),
]


class CryptoValueModel(BaseModel):
    """Immutable crypto value model."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )


class AliasedCryptoValueModel(CryptoValueModel):
    """Immutable crypto value model that accepts and serializes aliases."""

    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class EncryptedAnswerPayload(CryptoValueModel):
    """Ciphertext and nonce for one encrypted answer payload."""

    ciphertext: bytes = Field(min_length=1, repr=False)
    nonce: bytes


class DecryptedAnswerPayload(CryptoValueModel):
    """Parsed plaintext recovered from one encrypted answer payload."""

    question_node_id: UUID
    answer_state: SubmissionAnswerState
    answer_value: PlaintextAnswerValue


class SecretValue(AliasedCryptoValueModel):
    """A secret string and its AWS-assigned version identifier."""

    model_config = ConfigDict(extra="ignore")

    secret_string: NonEmptyStr = Field(
        validation_alias="SecretString",
        serialization_alias="SecretString",
    )
    version_id: NonEmptyStr = Field(
        validation_alias="VersionId",
        serialization_alias="VersionId",
    )


class LinkageSecretPayload(AliasedCryptoValueModel):
    """Decoded JSON payload stored inside the linkage secret."""

    version: PositiveVersion
    secret: Base64LinkageSecret = Field(
        validation_alias="secret_b64",
        serialization_alias="secret_b64",
    )


class _PlaintextPayloadBase(AliasedCryptoValueModel):
    """Shared plaintext answer payload metadata."""

    payload_version: PositiveVersion = Field(
        validation_alias="v",
        serialization_alias="v",
    )
    question_node_id: UUID
    answer_state: SubmissionAnswerState


class PlaintextPayload(_PlaintextPayloadBase):
    """Canonical JSON-safe plaintext answer payload before encryption."""

    answer_value: PlaintextAnswerValue


class PlaintextPayloadInput(_PlaintextPayloadBase):
    """Input shape that accepts app/API answer models before encryption."""

    answer_value: PlaintextAnswerValue | BaseModel

    @field_validator("answer_value", mode="before")
    @classmethod
    def _normalise_answer_value(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        return value

    def to_plaintext_payload(self) -> PlaintextPayload:
        return PlaintextPayload.model_validate(self.model_dump(mode="json"))
