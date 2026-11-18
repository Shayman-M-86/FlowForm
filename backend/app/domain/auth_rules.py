from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.domain.errors import (
    InvalidIdTokenSubjectError,
    MissingEmailClaimError,
    TokenSubjectMismatchError,
)
from app.schema.types import Auth0UserId


def ensure_subject(*, claims: Mapping[str, Any]) -> Auth0UserId:
    """Return the ID-token subject or raise an auth error."""
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidIdTokenSubjectError()
    try:
        return _AUTH0_USER_ID.validate_python(subject)
    except ValidationError as exc:
        raise InvalidIdTokenSubjectError() from exc


def ensure_subject_matches(*, access_token_sub: Auth0UserId, id_token_sub: Auth0UserId) -> None:
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


def extract_email_verified(*, claims: Mapping[str, Any]) -> bool:
    """Return the ID-token email_verified claim, defaulting to False."""
    verified = claims.get("email_verified", False)
    return bool(verified) if isinstance(verified, bool) else False


_AUTH0_USER_ID = TypeAdapter(Auth0UserId)
