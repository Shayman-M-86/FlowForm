import re
from typing import Any

from pydantic import Field

from app.schema.api import limits

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def int_id_field(*, default: int | None = None) -> Any:
    return Field(default=default, ge=limits.INT_ID_MIN, le=limits.INT_ID_MAX)


def required_int_id_field() -> Any:
    return Field(..., ge=limits.INT_ID_MIN, le=limits.INT_ID_MAX)


def validate_slug(value: str, *, field_label: str = "Slug") -> str:
    """Validate a URL-safe slug value.

    Rules: lowercase letters, numbers, and hyphens only; no leading/trailing
    or consecutive hyphens; 1 to ``limits.SLUG_MAX`` characters.
    """
    value = value.strip()
    if not value:
        raise ValueError(f"{field_label} must not be blank.")
    if len(value) > limits.SLUG_MAX:
        raise ValueError(f"{field_label} must be {limits.SLUG_MAX} characters or fewer.")
    if value != value.lower():
        raise ValueError(f"{field_label} must be lowercase.")
    if "--" in value:
        raise ValueError(f"{field_label} must not contain consecutive hyphens.")
    if not _SLUG_RE.match(value):
        raise ValueError(
            f"{field_label} may only contain lowercase letters, numbers, and hyphens, "
            f"and must not start or end with a hyphen."
        )
    return value
