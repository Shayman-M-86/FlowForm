"""Crypto layer errors."""

from __future__ import annotations

from app.core.errors import AppError

# ---------------------------------------------------------------------------
# Internal errors — not exposed to API consumers
# ---------------------------------------------------------------------------


class KmsError(Exception):
    """KMS wrap or unwrap operation failure (internal)."""


# ---------------------------------------------------------------------------
# App errors — translated into HTTP responses by the error handler
# ---------------------------------------------------------------------------


class LinkageKeyError(AppError):
    """A linkage key could not be loaded or validated."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=500,
            code="LINKAGE_KEY_ERROR",
            message=message,
        )


class PayloadDecodeError(AppError):
    """Decrypted plaintext bytes are not a supported payload."""

    def __init__(self, message: str = "Invalid plaintext payload") -> None:
        super().__init__(
            status_code=500,
            code="PAYLOAD_DECODE_ERROR",
            message=message,
        )


class LinkageKeyUnavailableError(AppError):
    """The linkage key service could not reach Secrets Manager."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="LINKAGE_KEY_UNAVAILABLE",
            message="Linkage key service is temporarily unavailable",
        )


class LinkageKeyVersionUnavailableError(AppError):
    """A specific linkage key version could not be loaded."""

    def __init__(self, version: int) -> None:
        super().__init__(
            status_code=503,
            code="LINKAGE_KEY_VERSION_UNAVAILABLE",
            message=f"Linkage key version {version} is unavailable",
        )


class SessionDEKUnavailableError(AppError):
    """The session DEK could not be unwrapped from KMS."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="SESSION_DEK_UNAVAILABLE",
            message="Session encryption key is temporarily unavailable",
        )


class SurveyBranchKeyUnavailableError(AppError):
    """The survey branch key could not be wrapped or unwrapped with KMS."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="SURVEY_BRANCH_KEY_UNAVAILABLE",
            message="Survey encryption key is temporarily unavailable",
        )
