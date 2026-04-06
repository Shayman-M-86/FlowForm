from typing import Any

from flask import Request
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType


def _get_json_object(request_obj: Request) -> dict[str, Any]:
    """Parse the request body as a JSON object.

    Raises:
        UnsupportedMediaType: The request body is not JSON.
        BadRequest: The JSON is malformed or the decoded body is not an object.
    """
    if not request_obj.is_json:
        raise UnsupportedMediaType("Request body must be JSON")

    body = request_obj.get_json()

    if not isinstance(body, dict):
        raise BadRequest("JSON body must be an object")

    return body


def parse[TModel: BaseModel](model_cls: type[TModel], request_obj: Request) -> TModel:
    """Parse the JSON request body into a Pydantic model.

    Raises:
        HTTPException: If the request body is invalid for the endpoint.
        ValidationError: If the JSON body does not satisfy the Pydantic model schema.
    """
    body = _get_json_object(request_obj)
    return model_cls.model_validate(body)


def parse_query[TModel: BaseModel](model_cls: type[TModel], request_obj: Request) -> TModel:
    """Parse the query string into a Pydantic model."""
    return model_cls.model_validate(request_obj.args.to_dict())


def normalize_pydantic_errors(exc: ValidationError) -> list[dict[str, object]]:
    """Convert Pydantic validation errors into a consistent format for API responses."""
    normalized: list[dict[str, object]] = []

    for err in exc.errors():
        normalized.append(
            {
                "field": ".".join(str(part) for part in err.get("loc", [])),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )

    return normalized
