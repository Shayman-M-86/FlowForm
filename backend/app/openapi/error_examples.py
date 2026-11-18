"""Examples derived from real protocol exceptions and current request validation.

Business-error constructors and database rule factories are deliberately not
executed to manufacture documentation. They may depend on runtime state.
"""

from pydantic import ValidationError
from werkzeug.exceptions import default_exceptions

from app.api.utils.errors import build_error_payload
from app.api.utils.validation import normalize_pydantic_errors
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest


def build_examples_by_status() -> dict[int, dict[str, dict]]:
    """Build representative HTTP errors plus a real Pydantic validation failure."""
    grouped = {}
    for status in (400, 401, 403, 404, 405, 409, 413, 415, 429, 500):
        error = default_exceptions[status]()
        grouped[status] = {
            error.name.replace(" ", ""): {
                "summary": error.name,
                "value": build_error_payload(code=f"HTTP_{status}", message=error.description or error.name),
            }
        }
    try:
        StartSubmissionSessionRequest.model_validate({})
    except ValidationError as error:
        grouped[422] = {
            "ValidationError": {
                "summary": "Invalid request",
                "value": build_error_payload(
                    code="VALIDATION_ERROR",
                    message="Request validation failed.",
                    details={"errors": normalize_pydantic_errors(error)},
                ),
            }
        }
    return grouped
