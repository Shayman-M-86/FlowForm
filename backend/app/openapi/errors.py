"""Reusable error response components for the generated OpenAPI spec.

These shapes mirror the JSON returned by ``register_error_handlers`` in
``app.api.utils.errors`` — they are documentation only and are not used at
runtime to format errors.

Every API error response shares one schema, ``ErrorResponse``::

    {
        "code": "MACHINE_READABLE_CODE",
        "message": "Human-readable description.",
        "details": { ... optional, structured extras ... }
    }

``details`` is omitted when empty. Pydantic validation errors place their
per-field error list under ``details.errors`` rather than at the top level,
so clients only have to handle one shape.
"""

from __future__ import annotations

from typing import Any

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


# Per-status example payloads. Attached on the response object so each status
# shows realistic content in Swagger UI instead of the same shared example.
_ERROR_EXAMPLES: dict[str, dict[str, Any]] = {
    "400": {
        "code": "INVALID_REQUEST",
        "message": "The request is invalid for this endpoint.",
    },
    "401": {
        "code": "INVALID_ACCESS_TOKEN",
        "message": "Access token is expired or invalid.",
    },
    "403": {
        "code": "FORBIDDEN",
        "message": "You do not have permission to access this resource.",
    },
    "404": {
        "code": "NOT_FOUND",
        "message": "The requested resource was not found.",
    },
    "409": {
        "code": "PROJECT_SLUG_CONFLICT",
        "message": "Project slug 'my-project' is already in use.",
    },
    "429": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Please retry after some time.",
    },
    "500": {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred.",
    },
}


# Two realistic 422 examples — Pydantic field-validation failures (the common
# case) and AppError-shaped multi-field invariants (e.g. SURVEY_VISIBILITY_
# MISMATCH). Both use the same ErrorResponse schema; clients distinguish via
# ``code``.
_VALIDATION_EXAMPLES: dict[str, dict[str, Any]] = {
    "pydantic_field_validation": {
        "summary": "Pydantic field validation failure",
        "value": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": {
                "errors": [
                    {
                        "field": "sort_key",
                        "message": "Input should be a valid integer.",
                        "type": "int_parsing",
                    },
                ],
            },
        },
    },
    "app_error_invariant": {
        "summary": "Multi-field invariant rejected by a domain rule",
        "value": {
            "code": "SURVEY_VISIBILITY_MISMATCH",
            "message": "public_slug is required when visibility is 'public'.",
        },
    },
}


def _error_ref() -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{ERROR_SCHEMA_NAME}"}


def _error_response(status: str, description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": _error_ref(),
                "example": _ERROR_EXAMPLES[status],
            }
        },
    }


def default_error_responses(*, include_auth: bool = True) -> dict[str, Any]:
    """Return the default error responses block attached to every operation."""
    responses: dict[str, Any] = {
        "400": _error_response("400", "Bad request."),
        "404": _error_response("404", "Resource not found."),
        "409": _error_response("409", "Conflict with the current resource state."),
        "422": {
            "description": "Request was syntactically valid but semantically invalid.",
            "content": {
                "application/json": {
                    "schema": _error_ref(),
                    "examples": _VALIDATION_EXAMPLES,
                }
            },
        },
        "429": _error_response("429", "Rate limit exceeded."),
        "500": _error_response("500", "Internal server error."),
    }

    if include_auth:
        responses["401"] = _error_response("401", "Authentication required or token invalid.")
        responses["403"] = _error_response("403", "Authenticated but not authorized for this resource.")

    return responses
