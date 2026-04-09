from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.errors import (
    InvalidIdTokenSubjectError,
    MissingEmailClaimError,
    TokenSubjectMismatchError,
)


def ensure_subject(*, claims: Mapping[str, Any]) -> str:
    """Return the ID-token subject or raise an auth error."""
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidIdTokenSubjectError()
    return subject


def ensure_subject_matches(*, access_token_sub: str, id_token_sub: str) -> None:
    """Ensure the access token and ID token describe the same user."""
    if id_token_sub != access_token_sub:
        raise TokenSubjectMismatchError()


def ensure_email(*, claims: Mapping[str, Any]) -> str:
    """Return the ID-token email or raise an auth error."""
    email = claims.get("email")
    if not isinstance(email, str) or not email.strip():
        raise MissingEmailClaimError()
    return email.strip()


def normalize_display_name(*, claims: Mapping[str, Any]) -> str | None:
    """Return a normalized optional display name from ID-token claims."""
    name = claims.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None
