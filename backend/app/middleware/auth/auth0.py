# ruff: noqa: E402
"""Auth0 integration; the warning filter must precede auth0-api-python imports."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import requests
from authlib.deprecate import AuthlibDeprecationWarning

warnings.filterwarnings(
    "ignore",
    category=AuthlibDeprecationWarning,
    module="auth0_api_python\\.api_client",
)

from auth0_api_python import ApiClient, ApiClientOptions
from auth0_api_python.errors import BaseAuthError
from auth0_api_python.utils import get_unverified_header
from authlib.jose import JsonWebKey, JsonWebToken
from flask import Flask, g, request

from app.core.config import Settings
from app.core.errors import ConfigError

from . import auth_errors

F = TypeVar("F", bound=Callable[..., Any])
logger = logging.getLogger(__name__)

# Refresh the M2M token this many seconds before it actually expires.
_MGMT_TOKEN_REFRESH_BUFFER = 60
_MGMT_REQUEST_TIMEOUT_SECONDS = 10
_MGMT_REQUIRED_SCOPES = frozenset(
    {
        "create:user_tickets",
        "create:users",
        "delete:guardian_enrollments",
        "delete:users",
        "update:users",
        "read:users",
    }
)
_MGMT_SCOPE_REQUEST = " ".join(sorted(_MGMT_REQUIRED_SCOPES))


class ManagementApiError(Exception):
    """Internal Auth0 Management API failure.

    ``message`` is intentionally generic so the exception does not expose
    provider payloads or user-linked identifiers if it escapes into a
    traceback. Provider details are kept in explicit attributes for controlled
    server-side logging at the service/startup boundary.
    """

    def __init__(
        self,
        *,
        status_code: int | None,
        provider_error: str | None = None,
        provider_message: str | None = None,
        message: str = "Auth0 Management API request failed.",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider_error = provider_error
        self.provider_message = provider_message


def _management_error_from_response(response: requests.Response) -> ManagementApiError:
    try:
        body = response.json()
    except ValueError:
        body = {}

    if not isinstance(body, dict):
        body = {}

    provider_error = body.get("error") or body.get("code") or getattr(response, "reason", None)
    provider_message = (
        body.get("error_description")
        or body.get("message")
        or response.text
        or provider_error
        or "Management API error"
    )

    return ManagementApiError(
        status_code=response.status_code,
        provider_error=str(provider_error) if provider_error is not None else None,
        provider_message=str(provider_message) if provider_message is not None else None,
    )


class ManagementApiClient:
    """Thin client for the Auth0 Management API v2.

    Obtains and caches a machine-to-machine token using client credentials.
    The token is refreshed automatically when it is within the refresh buffer.
    Thread-safe: a lock prevents concurrent refreshes.
    """

    def __init__(self, *, domain: str, client_id: str, client_secret: str) -> None:
        self._domain = domain
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = f"https://{domain}/api/v2"
        self._token_url = f"https://{domain}/oauth/token"
        self._mgmt_audience = f"https://{domain}/api/v2/"
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_scopes: set[str] = set()
        self._lock = threading.Lock()

    def _require_token_scopes(self, scopes: set[str]) -> None:
        """Ensure the cached Management API token contains the required scopes."""
        self._get_token()
        missing = scopes - self._token_scopes
        if missing:
            missing_scopes = ", ".join(sorted(missing))
            raise ManagementApiError(
                status_code=None,
                provider_error="missing_management_api_scope",
                provider_message=f"Management API token is missing required scope(s): {missing_scopes}.",
            )

    def _fetch_token(self) -> None:
        """Request a new M2M token from Auth0."""
        logger.debug("Fetching Auth0 M2M token for Management API (client_id=%s).", self._client_id)
        try:
            response = requests.post(
                self._token_url,
                json={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "audience": self._mgmt_audience,
                    "scope": _MGMT_SCOPE_REQUEST,
                },
                timeout=_MGMT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise ManagementApiError(
                status_code=None,
                provider_error="network_error",
                provider_message=str(exc),
            ) from exc

        if not response.ok:
            raise _management_error_from_response(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_token_response",
                provider_message=response.text,
            ) from exc

        if not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_token_response",
                provider_message="Token response did not include an access token.",
            )

        scope_value = data.get("scope")
        token_scopes = set(scope_value.split()) if isinstance(scope_value, str) else set()
        missing = _MGMT_REQUIRED_SCOPES - token_scopes
        if missing:
            missing_scopes = ", ".join(sorted(missing))
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="missing_management_api_scope",
                provider_message=f"Management API token is missing required scope(s): {missing_scopes}.",
            )
        self._access_token = data["access_token"]
        self._token_scopes = token_scopes
        expires_in = int(data.get("expires_in", 86400))
        self._token_expires_at = time.monotonic() + expires_in
        logger.debug("Auth0 M2M token acquired, expires in %ss.", expires_in)

    def _get_token(self) -> str:
        """Return a valid M2M access token, refreshing if necessary."""
        if self._access_token is None or time.monotonic() >= self._token_expires_at - _MGMT_TOKEN_REFRESH_BUFFER:
            with self._lock:
                # Double-checked locking: another thread may have refreshed already.
                if (
                    self._access_token is None
                    or time.monotonic() >= self._token_expires_at - _MGMT_TOKEN_REFRESH_BUFFER
                ):
                    self._fetch_token()
        return self._access_token  # type: ignore[return-value]

    def validate_connection(self) -> None:
        """Verify Management API credentials and required scopes."""
        self._require_token_scopes(set(_MGMT_REQUIRED_SCOPES))

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}", "Content-Type": "application/json"}

    def _raise_for_mgmt_error(self, response: requests.Response) -> None:
        if not response.ok:
            raise _management_error_from_response(response)

    def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> requests.Response:
        try:
            response = requests.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=json,
                timeout=_MGMT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise ManagementApiError(
                status_code=None,
                provider_error="network_error",
                provider_message=str(exc),
            ) from exc

        self._raise_for_mgmt_error(response)
        return response

    def update_user(
        self,
        auth0_user_id: str,
        *,
        display_name: str | None = None,
        nickname: str | None = None,
        picture: str | None = None,
        email: str | None = None,
        username: str | None = None,
    ) -> None:
        """Patch mutable fields on an Auth0 user record.

        Only fields explicitly passed (non-None) are sent. When ``email`` is
        changed Auth0 automatically resets ``email_verified`` to false.
        """
        payload: dict[str, Any] = {}
        if display_name is not None:
            payload["name"] = display_name
        if nickname is not None:
            payload["nickname"] = nickname
        if picture is not None:
            payload["picture"] = picture
        if email is not None:
            payload["email"] = email
        if username is not None:
            payload["username"] = username
        if not payload:
            return
        self._request("PATCH", f"/users/{auth0_user_id}", json=payload)

    def create_password_change_ticket(self, auth0_user_id: str) -> str:
        """Create a hosted Auth0 password-change ticket for the given user."""
        self._require_token_scopes({"create:user_tickets"})
        response = self._request(
            "POST",
            "/tickets/password-change",
            json={"user_id": auth0_user_id},
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_ticket_response",
                provider_message=response.text,
            ) from exc

        if not isinstance(data, dict) or not isinstance(data.get("ticket"), str) or not data["ticket"]:
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_ticket_response",
                provider_message="Password-change ticket response did not include a ticket URL.",
            )

        return data["ticket"]

    def delete_user(self, auth0_user_id: str) -> None:
        """Permanently delete a user from Auth0."""
        self._request("DELETE", f"/users/{auth0_user_id}")

    def send_verification_email(self, auth0_user_id: str) -> None:
        """Trigger an email-verification job for the given user."""
        self._request("POST", "/jobs/verification-email", json={"user_id": auth0_user_id})

    def get_user_email_verified(self, auth0_user_id: str) -> bool:
        """Return the live email_verified flag for a user from Auth0.

        Used as a lazy fallback check: a user may have completed Auth0's own
        native email-verification flow independently of this app's invite
        system, and this reflects that without requiring a webhook/event
        stream integration to keep state continuously in sync.
        """
        response = self._request("GET", f"/users/{auth0_user_id}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_user_response",
                provider_message=response.text,
            ) from exc

        if not isinstance(data, dict):
            raise ManagementApiError(
                status_code=response.status_code,
                provider_error="invalid_user_response",
                provider_message="User response was not a JSON object.",
            )

        return bool(data.get("email_verified", False))

    def mark_email_verified(self, auth0_user_id: str) -> None:
        """Mark a user's email as verified on Auth0.

        Deliberately a separate, single-purpose method rather than folded
        into update_user -- email_verified is a security-sensitive flag
        that should only ever be set True by a deliberate proof-of-control
        event (here: a successful token-based invitation accept), never as
        a side effect of an unrelated profile-field PATCH.
        """
        self._request("PATCH", f"/users/{auth0_user_id}", json={"email_verified": True})

    def clear_mfa_devices(self, auth0_user_id: str) -> None:
        """Remove all enrolled MFA authenticators for the given user."""
        self._request("DELETE", f"/users/{auth0_user_id}/authenticators")


class AuthExtension:
    """Flask extension to register AuthError handlers."""

    def __init__(self) -> None:
        self.api_client: ApiClient | None = None
        self.mgmt: ManagementApiClient | None = None
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

        mgmt_settings = self.settings.flowform.auth0.mgmt
        if mgmt_settings is not None:
            # The Management API (/api/v2) is not served on Auth0 custom
            # domains, so use the canonical tenant domain when one is
            # configured; otherwise fall back to the issuer domain.
            mgmt_domain = mgmt_settings.domain or self.settings.flowform.auth0.domain
            mgmt_client = ManagementApiClient(
                domain=mgmt_domain,
                client_id=mgmt_settings.id,
                client_secret=mgmt_settings.secret.get_secret_value(),
            )
            if getattr(mgmt_settings, "validate_on_startup", True):
                try:
                    mgmt_client.validate_connection()
                except ManagementApiError as exc:
                    msg = "Auth0 Management API client validation failed. Check the configured client grant and scopes."
                    logger.error(
                        "%s status=%s provider_error=%s provider_message=%r",
                        msg,
                        exc.status_code,
                        exc.provider_error,
                        exc.provider_message,
                    )
                    raise ConfigError(msg) from exc
            else:
                logger.warning(
                    "Auth0 Management API startup validation is disabled. "
                    "Management operations will still fail closed if the provider is unavailable."
                )
            self.mgmt = mgmt_client
            logger.info("Auth0 Management API client initialized.")
        else:
            logger.warning(
                "Auth0 Management API client is not configured. "
                "Account-management features will be unavailable. "
                "Set FLOWFORM_AUTH0_MGMT_ID and FLOWFORM_AUTH0_MGMT_SECRET_FILE to enable them."
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
