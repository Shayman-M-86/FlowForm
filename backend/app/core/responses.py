from typing import Any

from flask import jsonify



def success_response(data: Any = None, message: str = "ok", status_code: int = 200):
    """Create a success response.

    Args:
        data (Any, optional): The data to include in the response. Defaults to None.
        message (str, optional): The message to include in the response. Defaults to "ok".
        status_code (int, optional): The HTTP status code for the response. Defaults to 200.


    Returns:
        tuple: A tuple containing the JSON response and the HTTP status code.
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
    response = {
        "success": False,
        "message": message,
        "error": {
            "code": error_code,
            "details": details,
        },
    }
    return jsonify(response), status_code
