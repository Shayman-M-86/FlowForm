"""Security scheme definitions for the generated OpenAPI spec.

FlowForm uses Auth0-issued RS256 JWTs as bearer tokens. The scheme is declared
here and applied as a global security requirement in ``spec.py``.
"""

from __future__ import annotations

from typing import Any

BEARER_SCHEME_NAME = "BearerAuth"

BEARER_SECURITY_SCHEME: dict[str, Any] = {
    "type": "http",
    "scheme": "bearer",
    "bearerFormat": "JWT",
    "description": "Auth0-issued JWT access token. Send as `Authorization: Bearer <token>`.",
}


def global_security() -> list[dict[str, list[str]]]:
    return [{BEARER_SCHEME_NAME: []}]


def optional_security() -> list[dict[str, list[str]]]:
    return [{}, {BEARER_SCHEME_NAME: []}]
