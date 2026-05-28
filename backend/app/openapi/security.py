"""Security scheme definitions for the generated OpenAPI spec.

FlowForm uses Auth0-issued RS256 JWTs as bearer tokens. The scheme is declared
here and applied as a global security requirement in ``spec.py``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

BEARER_SCHEME_NAME = "BearerAuth"
AUTH0_OAUTH_SCHEME_NAME = "Auth0OAuth"

BEARER_SECURITY_SCHEME: dict[str, Any] = {
    "type": "http",
    "scheme": "bearer",
    "bearerFormat": "JWT",
    "description": "Auth0-issued JWT access token. Send as `Authorization: Bearer <token>`.",
}


def auth0_oauth_security_scheme(domain: str, audience: str) -> dict[str, Any]:
    """Return an Auth0 OAuth2 authorization-code scheme for Swagger UI."""
    base_url = f"https://{domain}"
    authorize_query = urlencode({"audience": audience})
    return {
        "type": "oauth2",
        "description": "Log in with Auth0 to get an access token for this API.",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": f"{base_url}/authorize?{authorize_query}",
                "tokenUrl": f"{base_url}/oauth/token",
                "scopes": {},
            }
        },
    }


def global_security(scheme_name: str = BEARER_SCHEME_NAME) -> list[dict[str, list[str]]]:
    return [{scheme_name: []}]


def optional_security(scheme_name: str = BEARER_SCHEME_NAME) -> list[dict[str, list[str]]]:
    return [{}, {scheme_name: []}]
