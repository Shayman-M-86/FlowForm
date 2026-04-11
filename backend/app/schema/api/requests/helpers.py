import re

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_slug(value: str, *, field_label: str = "Slug") -> str:
    """Validate a URL-safe slug value.

    Rules: lowercase letters, numbers, and hyphens only; no leading/trailing
    or consecutive hyphens; 1 to 80 characters.
    """
    value = value.strip()
    if not value:
        raise ValueError(f"{field_label} must not be blank.")
    if len(value) > 80:
        raise ValueError(f"{field_label} must be 80 characters or fewer.")
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
