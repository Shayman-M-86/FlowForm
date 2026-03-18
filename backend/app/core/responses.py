from typing import Any

from flask import jsonify



def success_response(data: Any = None, message: str = "ok", status_code: int = 200):
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
