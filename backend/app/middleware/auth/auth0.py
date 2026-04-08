from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from auth0_api_python import ApiClient, ApiClientOptions
from auth0_api_python.errors import BaseAuthError
from flask import Flask, g, request

from app.core.config import Settings
from app.core.errors import AuthError

F = TypeVar("F", bound=Callable[..., Any])


class AuthExtension:
    """Flask extension to register AuthError handlers."""

    def __init__(self) -> None:
        self.api_client: ApiClient | None = None

    def init_app(self, app: Flask) -> None:
        """Initialize the extension with the Flask app."""
        self.settings: Settings = app.extensions["settings"]

        self.api_client = ApiClient(
            ApiClientOptions(
                audience=self.settings.flowform.auth0.audience,
                domain=self.settings.flowform.auth0.domain,
            )
        )

    def _extract_bearer_token(self) -> str:
        """Return the bearer token from the Authorization header."""
        auth_header = request.headers.get("Authorization", "").strip()
        parts = auth_header.split()

        if not parts:
            raise AuthError(
                message="Authorization header is expected.",
                code="MISSING_AUTHORIZATION_HEADER",
                status_code=401,
            )

        if parts[0].lower() != "bearer":
            raise AuthError(
                message="Authorization header must start with Bearer.",
                code="INVALID_AUTHORIZATION_HEADER",
                status_code=401,
            )

        if len(parts) != 2:
            raise AuthError(
                message="Authorization header must be Bearer <token>.",
                code="INVALID_AUTHORIZATION_HEADER",
                status_code=401,
            )

        return parts[1]

    def _verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an Auth0 access token and return its claims."""
        if self.api_client is None:
            raise AuthError(
                message="AuthExtension is not initialized with an API client.",
                code="AUTH_EXTENSION_NOT_INITIALIZED",
                status_code=500,
            )
        try:
            claims = asyncio.run(self.api_client.verify_access_token(token))
        except BaseAuthError as exc:
            raise AuthError(
                message=str(exc),
                code="INVALID_ACCESS_TOKEN",
                status_code=exc.get_status_code(),
                headers=exc.get_headers() or {},
            ) from exc

        if not isinstance(claims, dict):
            raise AuthError(
                message="Token claims payload was not an object.",
                code="INVALID_ACCESS_TOKEN_CLAIMS",
                status_code=401,
            )

        return claims

    def _require_scope(self, claims: dict[str, Any], required_scope: str) -> None:
        """Ensure the verified token contains the required scope."""
        token_scopes = set(str(claims.get("scope", "")).split())

        if required_scope not in token_scopes:
            raise AuthError(
                message=f"Missing required scope: {required_scope}",
                code="INSUFFICIENT_SCOPE",
                status_code=403,
                details={"required_scope": required_scope},
            )

    def require_auth(self, required_scope: str | None = None) -> Callable[[F], F]:
        """Protect a Flask route with Auth0 access-token verification."""

        def decorator(fn: F) -> F:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):
                token = self._extract_bearer_token()
                claims = self._verify_access_token(token)

                if required_scope is not None:
                    self._require_scope(claims, required_scope)

                g.user_claims = claims
                g.user_sub = claims.get("sub")

                return fn(*args, **kwargs)

            return cast(F, wrapper)

        return decorator

    def get_current_claims(self) -> dict[str, Any]:
        """Return the verified claims stored on flask.g for this request."""
        claims = getattr(g, "user_claims", None)

        if not isinstance(claims, dict):
            raise AuthError(
                message="Authenticated user claims were not found on the request context.",
                code="MISSING_AUTH_CONTEXT",
                status_code=401,
            )

        return claims

    def get_current_user_sub(self) -> str:
        """Return the Auth0 subject claim for the current request."""
        claims = self.get_current_claims()
        sub = claims.get("sub")

        if not isinstance(sub, str) or not sub:
            raise AuthError(
                message="Authenticated token did not contain a valid subject.",
                code="MISSING_SUB_CLAIM",
                status_code=401,
            )

        return sub
