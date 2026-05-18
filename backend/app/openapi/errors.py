"""Reusable error response components for the generated OpenAPI spec.

Schema and response examples mirror the JSON returned by
``register_error_handlers`` in ``app.api.utils.errors``. The schema is a
single ``ErrorResponse`` shape; examples are **derived at spec-build time**
from real ``AppError`` subclasses and the DB integrity rule registry so they
stay in sync with the runtime as new errors are added.

See ``app/openapi/error_examples.py`` for the derivation logic.
"""

from __future__ import annotations

from typing import Any

from app.openapi.error_examples import build_examples_by_status

ERROR_SCHEMA_NAME = "ErrorResponse"

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {
            "type": "string",
            "description": "Machine-readable error code.",
        },
        "message": {
            "type": "string",
            "description": "Human-readable error message.",
        },
        "details": {
            "type": "object",
            "description": (
                "Optional structured extras. Pydantic validation errors place "
                "their per-field failures here as ``details.errors``."
            ),
            "additionalProperties": True,
        },
    },
}


_STATUS_DESCRIPTIONS: dict[int, str] = {
    400: "Bad request.",
    401: "Authentication required or token invalid.",
    403: "Authenticated but not authorized for this resource.",
    404: "Resource not found.",
    409: "Conflict with the current resource state.",
    422: "Request was syntactically valid but semantically invalid.",
    429: "Rate limit exceeded.",
    500: "Internal server error.",
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


def default_error_responses(*, include_auth: bool = True) -> dict[str, Any]:
    """Return the default error responses block attached to every operation.

    Examples are derived from real error classes via
    :func:`build_examples_by_status`; descriptions come from a small static
    table because they characterise *the response*, not any one example.
    """
    by_status = build_examples_by_status()

    statuses: list[int] = [400, 404, 409, 422, 429, 500]
    if include_auth:
        statuses.extend([401, 403])
    statuses = sorted(set(statuses))

    return {
        str(status): _response_with_examples(
            _STATUS_DESCRIPTIONS.get(status, ""),
            by_status.get(status, {}),
        )
        for status in statuses
    }
