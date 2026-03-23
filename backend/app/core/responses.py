from typing import Any

from flask import jsonify


def success_response(data: Any = None, message: str = "ok", status_code: int = 200):
    """Return a standard JSON success envelope.

    Args:
        data: (Optional) Payload to include in the response.
        message: Human-readable success message.
        status_code: HTTP status code for the response.

    Returns:
        JSON response object and status code.
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
    }
    return jsonify(response), status_code



def error_response(
    message: str,
    error_code: str,
    details: Any = None,
    status_code: int = 400,
):
    """Return a standard JSON error envelope.

    Args:
        message: Error message to present to the client.
        error_code: Application-specific error identifier.
        details: (Optional) Structured error details.
        status_code: HTTP status code for the response.

    Returns:
        JSON response object and status code.
    """
    response = {
        "success": False,
        "message": message,
        "error": {
            "code": error_code,
            "details": details,
        },
    }
    return jsonify(response), status_code
