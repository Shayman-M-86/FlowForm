"""OpenAPI error components derived from the runtime error payload contract."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import Field, TypeAdapter

from app.api.utils.errors import ErrorPayload
from app.openapi.error_examples import build_examples_by_status

# Preserve the public component name while deriving its shape from the runtime contract.
ErrorResponse = Annotated[ErrorPayload, Field(title="ErrorResponse")]
ERROR_SCHEMA_NAME = "ErrorResponse"
ERROR_SCHEMA: dict[str, Any] = TypeAdapter(ErrorResponse).json_schema()


_STATUS_DESCRIPTIONS: dict[int, str] = {
    400: "Bad request.",
    401: "Authentication required or token invalid.",
    403: "Authenticated but not authorized for this resource.",
    404: "Resource not found.",
    409: "Conflict with the current resource state.",
    422: "Request was syntactically valid but semantically invalid.",
    429: "Rate limit exceeded.",
    500: "Internal server error.",
    502: "Upstream service failed to provide a usable response.",
    503: "Service unavailable.",
}

_STATUS_RESPONSE_COMPONENTS: dict[int, str] = {
    400: "BadRequestError",
    401: "UnauthorizedError",
    403: "ForbiddenError",
    404: "NotFoundError",
    405: "MethodNotAllowedError",
    413: "RequestEntityTooLargeError",
    415: "UnsupportedMediaTypeError",
    409: "ConflictError",
    422: "ValidationError",
    429: "RateLimitError",
    500: "InternalServerError",
    502: "BadGatewayError",
    503: "ServiceUnavailableError",
}


def _error_ref() -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{ERROR_SCHEMA_NAME}"}


def _response_with_examples(
    description: str,
    examples: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a response object that uses the OpenAPI ``examples:`` map."""
    media_type: dict[str, Any] = {"schema": _error_ref()}
    if examples:
        media_type["examples"] = examples
    return {
        "description": description,
        "content": {"application/json": media_type},
    }


def _error_statuses(*, include_auth: bool, additional: Iterable[int]) -> list[int]:
    statuses: list[int] = [400, 404, 405, 409, 413, 415, 422, 429, 500]
    if include_auth:
        statuses.extend([401, 403])
    return sorted(set(statuses).union(additional))


def default_error_response_components(
    *, include_auth: bool = True, additional: Iterable[int] = ()
) -> dict[str, dict[str, Any]]:
    """Return reusable default error response components.

    Examples are derived from real error classes via
    :func:`build_examples_by_status`; descriptions come from a small static
    table because they characterise *the response*, not any one example.
    """
    by_status = build_examples_by_status()

    return {
        _STATUS_RESPONSE_COMPONENTS[status]: _response_with_examples(
            _STATUS_DESCRIPTIONS.get(status, ""),
            by_status.get(status, {}),
        )
        for status in _error_statuses(include_auth=include_auth, additional=additional)
    }


def default_error_response_refs(
    *, include_auth: bool = True, additional: Iterable[int] = ()
) -> dict[str, dict[str, str]]:
    """Return default operation responses as bare $ref objects.

    The description lives on the reusable component in components/responses —
    repeating it per-operation adds hundreds of lines with no benefit.
    """
    return {
        str(status): {"$ref": f"#/components/responses/{_STATUS_RESPONSE_COMPONENTS[status]}"}
        for status in _error_statuses(include_auth=include_auth, additional=additional)
    }
