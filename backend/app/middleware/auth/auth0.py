from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import requests
from auth0_api_python import ApiClient, ApiClientOptions
from auth0_api_python.errors import BaseAuthError
from auth0_api_python.utils import get_unverified_header
from authlib.jose import JsonWebKey, JsonWebToken
from flask import Flask, g, request

from app.core.config import Settings
from app.core.errors import AuthError

F = TypeVar("F", bound=Callable[..., Any])


class AuthExtension:
    """Flask extension to register AuthError handlers."""

    def __init__(self) -> None:
        self.api_client: ApiClient | None = None
        self._id_token_jwt = JsonWebToken(["RS256"])
        self._oidc_metadata: dict[str, Any] | None = None
        self._jwks_data: dict[str, Any] | None = None

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

    def _discover_oidc_metadata(self) -> dict[str, Any]:
        """Load and cache the Auth0 OIDC metadata document."""
        if self._oidc_metadata is None:
            response = requests.get(
                f"https://{self.settings.flowform.auth0.domain}/.well-known/openid-configuration",
                timeout=10,
            )
            response.raise_for_status()
            metadata = response.json()

            if not isinstance(metadata, dict):
                raise AuthError(
                    message="OIDC metadata response was not an object.",
                    code="INVALID_OIDC_METADATA",
                    status_code=500,
                )

            self._oidc_metadata = metadata

        return self._oidc_metadata

    def _load_jwks(self) -> dict[str, Any]:
        """Load and cache the Auth0 JWKS document."""
        if self._jwks_data is None:
            metadata = self._discover_oidc_metadata()
            jwks_uri = metadata.get("jwks_uri")

            if not isinstance(jwks_uri, str) or not jwks_uri:
                raise AuthError(
                    message="OIDC metadata did not contain a JWKS URI.",
                    code="INVALID_OIDC_METADATA",
                    status_code=500,
                )

            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()

            if not isinstance(jwks_data, dict) or not isinstance(jwks_data.get("keys"), list):
                raise AuthError(
                    message="JWKS response was invalid.",
                    code="INVALID_JWKS",
                    status_code=500,
                )

            self._jwks_data = jwks_data

        return self._jwks_data

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify an Auth0 ID token and return its claims."""
        if not id_token:
            raise AuthError(
                message="ID token is required.",
                code="MISSING_ID_TOKEN",
                status_code=400,
            )

        expected_client_id = self.settings.flowform.auth0.client_id
        if not expected_client_id:
            raise AuthError(
                message="Auth0 client ID is not configured.",
                code="AUTH0_CLIENT_ID_NOT_CONFIGURED",
                status_code=500,
            )

        try:
            header = get_unverified_header(id_token)
            kid = header["kid"]
        except Exception as exc:
            raise AuthError(
                message=f"Failed to parse ID token header: {exc}",
                code="INVALID_ID_TOKEN",
                status_code=401,
            ) from exc

        jwks_data = self._load_jwks()
        matching_key_dict = next(
            (key_dict for key_dict in jwks_data["keys"] if key_dict.get("kid") == kid),
            None,
        )

        if matching_key_dict is None:
            raise AuthError(
                message=f"No matching key found for ID token kid: {kid}",
                code="INVALID_ID_TOKEN",
                status_code=401,
            )

        public_key = JsonWebKey.import_key(matching_key_dict)

        try:
            # Authlib returns a Key here, but the published type for decode()
            # does not include it even though the runtime accepts it.
            claims = self._id_token_jwt.decode(id_token, cast(Any, public_key))
        except Exception as exc:
            raise AuthError(
                message=f"ID token signature verification failed: {exc}",
                code="INVALID_ID_TOKEN",
                status_code=401,
            ) from exc

        metadata = self._discover_oidc_metadata()
        issuer = metadata.get("issuer")
        if claims.get("iss") != issuer:
            raise AuthError(
                message="ID token issuer mismatch.",
                code="INVALID_ID_TOKEN",
                status_code=401,
            )

        actual_aud = claims.get("aud")
        if isinstance(actual_aud, list):
            if expected_client_id not in actual_aud:
                raise AuthError(
                    message="ID token audience mismatch.",
                    code="INVALID_ID_TOKEN",
                    status_code=401,
                )
        elif actual_aud != expected_client_id:
            raise AuthError(
                message="ID token audience mismatch.",
                code="INVALID_ID_TOKEN",
                status_code=401,
            )

        now = int(time.time())
        if "exp" not in claims or now >= claims["exp"]:
            raise AuthError(
                message="ID token is expired.",
                code="INVALID_ID_TOKEN",
                status_code=401,
            )

        if "iat" not in claims:
            raise AuthError(
                message="ID token is missing the issued-at claim.",
                code="INVALID_ID_TOKEN",
                status_code=401,
            )

        return dict(claims)

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
