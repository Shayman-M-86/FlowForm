from __future__ import annotations

from app.core.errors import AuthError


def missing_authorization_header() -> AuthError:
    return AuthError(
        message="Authorization header is expected.",
        code="MISSING_AUTHORIZATION_HEADER",
        status_code=401,
    )


def invalid_authorization_header() -> AuthError:
    return AuthError(
        message="Authorization header must be Bearer <token>.",
        code="INVALID_AUTHORIZATION_HEADER",
        status_code=401,
    )


def invalid_authorization_header_scheme() -> AuthError:
    return AuthError(
        message="Authorization header must start with Bearer.",
        code="INVALID_AUTHORIZATION_HEADER",
        status_code=401,
    )


def auth_extension_not_initialized() -> AuthError:
    return AuthError(
        message="AuthExtension is not initialized with an API client.",
        code="AUTH_EXTENSION_NOT_INITIALIZED",
        status_code=500,
    )


def invalid_access_token(
    message: str,
    *,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> AuthError:
    return AuthError(
        message=message,
        code="INVALID_ACCESS_TOKEN",
        status_code=status_code,
        headers=headers or {},
    )


def invalid_access_token_claims() -> AuthError:
    return AuthError(
        message="Token claims payload was not an object.",
        code="INVALID_ACCESS_TOKEN_CLAIMS",
        status_code=401,
    )


def invalid_oidc_metadata_response() -> AuthError:
    return AuthError(
        message="OIDC metadata response was not an object.",
        code="INVALID_OIDC_METADATA",
        status_code=500,
    )


def invalid_oidc_metadata_missing_jwks_uri() -> AuthError:
    return AuthError(
        message="OIDC metadata did not contain a JWKS URI.",
        code="INVALID_OIDC_METADATA",
        status_code=500,
    )


def invalid_jwks() -> AuthError:
    return AuthError(
        message="JWKS response was invalid.",
        code="INVALID_JWKS",
        status_code=500,
    )


def missing_id_token() -> AuthError:
    return AuthError(
        message="ID token is required.",
        code="MISSING_ID_TOKEN",
        status_code=400,
    )


def auth0_client_id_not_configured() -> AuthError:
    return AuthError(
        message="Auth0 client ID is not configured.",
        code="AUTH0_CLIENT_ID_NOT_CONFIGURED",
        status_code=500,
    )


def invalid_id_token(message: str) -> AuthError:
    return AuthError(
        message=message,
        code="INVALID_ID_TOKEN",
        status_code=401,
    )


def insufficient_scope(required_scope: str) -> AuthError:
    return AuthError(
        message=f"Missing required scope: {required_scope}",
        code="INSUFFICIENT_SCOPE",
        status_code=403,
        details={"required_scope": required_scope},
    )


def missing_auth_context() -> AuthError:
    return AuthError(
        message="Authenticated user claims were not found on the request context.",
        code="MISSING_AUTH_CONTEXT",
        status_code=401,
    )


def missing_sub_claim() -> AuthError:
    return AuthError(
        message="Authenticated token did not contain a valid subject.",
        code="MISSING_SUB_CLAIM",
        status_code=401,
    )
