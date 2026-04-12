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

from . import auth_errors

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
            raise auth_errors.missing_authorization_header()

        if parts[0].lower() != "bearer":
            raise auth_errors.invalid_authorization_header_scheme()

        if len(parts) != 2:
            raise auth_errors.invalid_authorization_header()

        return parts[1]

    def _clear_auth_context(self) -> None:
        """Clear any authenticated user context from the current request."""
        g.user_claims = None
        g.user_sub = None

    def _store_auth_context(self, claims: dict[str, Any]) -> None:
        """Store verified token claims on the current request context."""
        g.user_claims = claims
        g.user_sub = claims.get("sub")

    def _verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an Auth0 access token and return its claims."""
        if self.api_client is None:
            raise auth_errors.auth_extension_not_initialized()
        try:
            claims = asyncio.run(self.api_client.verify_access_token(token))
        except BaseAuthError as exc:
            raise auth_errors.invalid_access_token(
                str(exc),
                status_code=exc.get_status_code(),
                headers=exc.get_headers() or {},
            ) from exc

        if not isinstance(claims, dict):
            raise auth_errors.invalid_access_token_claims()

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
                raise auth_errors.invalid_oidc_metadata_response()

            self._oidc_metadata = metadata

        return self._oidc_metadata

    def _load_jwks(self) -> dict[str, Any]:
        """Load and cache the Auth0 JWKS document."""
        if self._jwks_data is None:
            metadata = self._discover_oidc_metadata()
            jwks_uri = metadata.get("jwks_uri")

            if not isinstance(jwks_uri, str) or not jwks_uri:
                raise auth_errors.invalid_oidc_metadata_missing_jwks_uri()

            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()

            if not isinstance(jwks_data, dict) or not isinstance(jwks_data.get("keys"), list):
                raise auth_errors.invalid_jwks()

            self._jwks_data = jwks_data

        return self._jwks_data

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify an Auth0 ID token and return its claims."""
        if not id_token:
            raise auth_errors.missing_id_token()

        expected_client_id = self.settings.flowform.auth0.client_id
        if not expected_client_id:
            raise auth_errors.auth0_client_id_not_configured()

        try:
            header = get_unverified_header(id_token)
            kid = header["kid"]
        except Exception as exc:
            raise auth_errors.invalid_id_token(f"Failed to parse ID token header: {exc}") from exc

        jwks_data = self._load_jwks()
        matching_key_dict = next(
            (key_dict for key_dict in jwks_data["keys"] if key_dict.get("kid") == kid),
            None,
        )

        if matching_key_dict is None:
            raise auth_errors.invalid_id_token(f"No matching key found for ID token kid: {kid}")

        public_key = JsonWebKey.import_key(matching_key_dict)

        try:
            # Authlib returns a Key here, but the published type for decode()
            # does not include it even though the runtime accepts it.
            claims = self._id_token_jwt.decode(id_token, cast(Any, public_key))
        except Exception as exc:
            raise auth_errors.invalid_id_token(f"ID token signature verification failed: {exc}") from exc

        metadata = self._discover_oidc_metadata()
        issuer = metadata.get("issuer")
        if claims.get("iss") != issuer:
            raise auth_errors.invalid_id_token("ID token issuer mismatch.")

        actual_aud = claims.get("aud")
        if isinstance(actual_aud, list):
            if expected_client_id not in actual_aud:
                raise auth_errors.invalid_id_token("ID token audience mismatch.")
        elif actual_aud != expected_client_id:
            raise auth_errors.invalid_id_token("ID token audience mismatch.")

        now = int(time.time())
        if "exp" not in claims or now >= claims["exp"]:
            raise auth_errors.invalid_id_token("ID token is expired.")

        if "iat" not in claims:
            raise auth_errors.invalid_id_token("ID token is missing the issued-at claim.")

        return dict(claims)

    def _require_scope(self, claims: dict[str, Any], required_scope: str) -> None:
        """Ensure the verified token contains the required scope."""
        token_scopes = set(str(claims.get("scope", "")).split())

        if required_scope not in token_scopes:
            raise auth_errors.insufficient_scope(required_scope)

    def require_auth(self, required_scope: str | None = None) -> Callable[[F], F]:
        """Protect a Flask route with Auth0 access-token verification."""

        def decorator(fn: F) -> F:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):
                self._clear_auth_context()
                token = self._extract_bearer_token()
                claims = self._verify_access_token(token)

                if required_scope is not None:
                    self._require_scope(claims, required_scope)

                self._store_auth_context(claims)

                return fn(*args, **kwargs)

            return cast(F, wrapper)

        return decorator

    def optional_auth(self) -> Callable[[F], F]:
        """Allow anonymous access while populating auth context when a valid token is present."""

        def decorator(fn: F) -> F:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):
                self._clear_auth_context()

                if not request.headers.get("Authorization", "").strip():
                    return fn(*args, **kwargs)

                token = self._extract_bearer_token()
                claims = self._verify_access_token(token)
                self._store_auth_context(claims)

                return fn(*args, **kwargs)

            return cast(F, wrapper)

        return decorator

    def get_optional_current_claims(self) -> dict[str, Any] | None:
        """Return verified claims for this request, or None when anonymous."""
        claims = getattr(g, "user_claims", None)
        return claims if isinstance(claims, dict) else None

    def get_optional_current_user_sub(self) -> str | None:
        """Return the current Auth0 subject claim, or None when anonymous."""
        claims = self.get_optional_current_claims()

        if claims is None:
            return None

        sub = claims.get("sub")
        return sub if isinstance(sub, str) and sub else None

    def get_current_claims(self) -> dict[str, Any]:
        """Return the verified claims stored on flask.g for this request."""
        claims = self.get_optional_current_claims()

        if not isinstance(claims, dict):
            raise auth_errors.missing_auth_context()

        return claims

    def get_current_user_sub(self) -> str:
        """Return the Auth0 subject claim for the current request."""
        sub = self.get_optional_current_user_sub()

        if not isinstance(sub, str) or not sub:
            raise auth_errors.missing_sub_claim()

        return sub
